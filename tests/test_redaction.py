"""Synthetic regression coverage: no real Redmine server or credentials."""
import copy
import json
import logging
from urllib.parse import quote

import httpx
import pytest
import yaml

from mcp_redmine import server
from mcp_redmine.redaction import REDACTED, redact_text

FAKE_KEY = "fake-config-key/with+punctuation&quotes\""
OTHER_KEY = "fake-other-user-key"


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setattr(server, "REDMINE_API_KEY", FAKE_KEY)
    monkeypatch.setattr(server, "REDMINE_HEADERS", {})


@pytest.fixture(params=["yaml", "json"])
def output_format(request, monkeypatch):
    monkeypatch.setattr(server, "REDMINE_RESPONSE_FORMAT", request.param)
    return yaml.safe_load if request.param == "yaml" else json.loads


def mock_http(monkeypatch, status=200, body=None, content=None):
    calls = []

    def respond(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return httpx.Response(status, json=body, content=content,
                              request=httpx.Request(method, url))

    monkeypatch.setattr(server._http_client, "request", respond)
    return calls


def unwrap(result):
    return result.split("\n", 1)[1].rsplit("\n", 1)[0]


@pytest.mark.parametrize("path,method", [
    ("users/current.json", "get"), ("users/5.json", "get"),
    ("my/account.json", "get"), ("users.json", "post"),
])
def test_user_credentials_redacted_at_tool_boundary(monkeypatch, output_format, path, method):
    body = {"user": {"id": 5, "name": "測試成員", "api_key": OTHER_KEY,
                     "memberships": [{"project": {"id": 7, "name": "測試專案"}}]}}
    calls = mock_http(monkeypatch, body=body)
    result = server.redmine_request(path, method=method)
    parsed = output_format(unwrap(result))
    assert parsed == {"status_code": 200, "body": {
        "user": {**body["user"], "api_key": REDACTED}}, "error": ""}
    assert OTHER_KEY not in result
    assert calls[0]["headers"]["X-Redmine-API-Key"] == FAKE_KEY
    assert calls[0]["url"].startswith("https://redmine.example.org/")


@pytest.mark.parametrize("name", ["api_key", "API_KEY", "apiKey", "Api-Key", "API KEY",
                                  "X-Redmine-API-Key"])
def test_nested_sensitive_fields_and_non_mutation(output_format, name):
    data = {"items": [{"nested": {name: {"secret": OTHER_KEY}, "id": 3}}],
            "token": "ordinary-token", "upload": {"token": "7.fake-upload-token"},
            "passwd_changed_on": "2026-10-01", "generate_password": True}
    original = copy.deepcopy(data)
    result = server.format_response(data)
    parsed = output_format(result)
    assert parsed["items"][0]["nested"][name] == REDACTED
    assert OTHER_KEY not in result
    assert parsed["upload"] == data["upload"]
    assert parsed["token"] == data["token"]
    assert parsed["passwd_changed_on"] == data["passwd_changed_on"]
    assert parsed["generate_password"] is True
    assert data == original


@pytest.mark.parametrize("status", [200, 422, 500])
@pytest.mark.parametrize("kind", ["json", "text"])
def test_success_and_failure_echoes(monkeypatch, output_format, status, kind):
    text = f'api_key="{OTHER_KEY}"; echoed {FAKE_KEY}; query={quote(FAKE_KEY, safe="")}'
    if kind == "json":
        mock_http(monkeypatch, status=status, body={"api_key": OTHER_KEY, "errors": [text]})
    else:
        mock_http(monkeypatch, status=status, content=text.encode())
    result = server.redmine_request("issues.json")
    parsed = output_format(unwrap(result))
    assert parsed["status_code"] == status
    assert OTHER_KEY not in result and FAKE_KEY not in result
    assert quote(FAKE_KEY, safe="") not in result
    # YAML encodes bytes as !!binary: check the decoded payload too.
    if isinstance(parsed["body"], bytes):
        assert OTHER_KEY.encode() not in parsed["body"]
        assert FAKE_KEY.encode() not in parsed["body"]
    assert REDACTED in str(parsed["body"])


@pytest.mark.parametrize("encoder", [
    lambda s: s, lambda s: json.dumps(s)[1:-1],
    lambda s: quote(s, safe=""),
    lambda s: "".join(f"%{b:02x}" for b in s.encode()),
    lambda s: "".join(f"%{b:02X}" for b in s.encode()),
    lambda s: s.replace("&", "&amp;").replace('"', "&quot;"),
])
def test_supported_encodings(encoder):
    encoded = encoder(FAKE_KEY)
    assert redact_text("echo=" + encoded, [FAKE_KEY]) == "echo=" + REDACTED


def test_exception_and_refused_url_are_redacted(monkeypatch, output_format):
    def fail(*args, **kwargs):
        raise RuntimeError(f"request failed with {FAKE_KEY} and api_key={OTHER_KEY}")

    monkeypatch.setattr(server._http_client, "request", fail)
    result = server.redmine_request("issues.json")
    parsed = output_format(unwrap(result))
    assert parsed["status_code"] == 0
    assert OTHER_KEY not in result and FAKE_KEY not in result
    refused = server.redmine_request(f"https://other.example/{quote(FAKE_KEY, safe='')}")
    assert "escapes REDMINE_URL" in refused
    assert quote(FAKE_KEY, safe="") not in refused


def test_custom_authentication_header_echo(monkeypatch, output_format):
    monkeypatch.setattr(server, "REDMINE_HEADERS", {"X-Redmine-API-Key": OTHER_KEY})
    calls = mock_http(monkeypatch, body={"message": OTHER_KEY})
    result = server.redmine_request("issues.json")
    assert calls[0]["headers"]["X-Redmine-API-Key"] == OTHER_KEY
    assert output_format(unwrap(result))["body"]["message"] == REDACTED


@pytest.mark.parametrize("path,method,data,body", [
    ("issues.json", "post", {"issue": {"subject": "測試", "assigned_to_id": 5}}, {"issue": {"id": 9}}),
    ("issues/9.json", "get", None, {"issue": {"id": 9, "subject": "測試", "assigned_to": {"id": 5}}}),
    ("issues/9.json", "put", {"issue": {"subject": "更新"}}, None),
    ("issues/9.json", "delete", None, None),
    ("time_entries.json", "post", {"time_entry": {"issue_id": 9, "hours": 2}}, {"time_entry": {"id": 1}}),
    ("issues/9/relations.json", "post", {"relation": {"issue_to_id": 10}}, {"relation": {"id": 1}}),
    ("projects.json", "get", None, {"projects": [{"id": 7, "name": "測試專案"}]}),
    ("projects/7/memberships.json", "get", None, {"memberships": [{"user": {"id": 5, "name": "成員"}}]}),
])
def test_workflow_payloads_unchanged(monkeypatch, output_format, path, method, data, body):
    calls = mock_http(monkeypatch, body=body)
    result = output_format(unwrap(server.redmine_request(path, method=method, data=data)))
    assert result == {"status_code": 200, "body": body, "error": ""}
    assert calls[0]["json"] == data


def test_upload_token_remains_usable(monkeypatch, tmp_path, output_format):
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path])
    path = tmp_path / "example.txt"
    path.write_bytes(b"example upload")
    upload = {"upload": {"id": 7, "token": "7.fake-upload-token", "api_key": OTHER_KEY}}
    calls = mock_http(monkeypatch, status=201, body=upload)
    result = output_format(server.redmine_upload(str(path)))
    assert result["body"]["upload"]["token"] == upload["upload"]["token"]
    assert result["body"]["upload"]["api_key"] == REDACTED
    assert calls[0]["content"] == path.read_bytes()
    mock_http(monkeypatch, status=201, body={"issue": {"id": 9}})
    data = {"issue": {"uploads": [{"token": result["body"]["upload"]["token"]}]}}
    assert output_format(unwrap(server.redmine_request("issues.json", method="post", data=data)))["status_code"] == 201


@pytest.mark.parametrize("tool", ["upload", "download", "image"])
def test_attachment_errors_use_same_boundary(monkeypatch, tmp_path, output_format, tool):
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path])
    path = tmp_path / "example.txt"
    path.write_text("example")
    mock_http(monkeypatch, status=403, body={"api_key": OTHER_KEY, "error": FAKE_KEY})
    result = {"upload": lambda: server.redmine_upload(str(path)),
              "download": lambda: server.redmine_download(1, str(tmp_path / "saved.txt")),
              "image": lambda: server.redmine_attachment_image(1)}[tool]()
    assert output_format(result)["status_code"] == 403
    assert OTHER_KEY not in result and FAKE_KEY not in result


@pytest.mark.parametrize("tool", ["upload", "download", "image"])
def test_attachment_exceptions_and_validation(monkeypatch, tmp_path, output_format, tool):
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path])
    path = tmp_path / "example.txt"
    path.write_text("example")

    def fail(*args, **kwargs):
        raise OSError(FAKE_KEY)

    monkeypatch.setattr(server, "request", fail)
    if tool == "upload":
        result = server.redmine_upload(str(path))
    elif tool == "download":
        result = server.redmine_download(1, str(tmp_path / "saved.txt"))
    else:
        result = server.redmine_attachment_image(1)
    assert output_format(result)["status_code"] == 0
    assert FAKE_KEY not in result
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [])
    result = server.redmine_upload("/not-allowed/" + OTHER_KEY + ".txt")
    assert "disabled" in result


def test_raw_attachment_bytes_are_unchanged(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path])
    payload = json.dumps({"api_key": OTHER_KEY, "echo": FAKE_KEY}).encode()
    mock_http(monkeypatch, content=payload)
    assert server.request("attachments/download/1/example.json", raw=True)["body"] == payload
    path = tmp_path / "saved.json"
    server.redmine_download(1, str(path), filename="example.json")
    assert path.read_bytes() == payload


def test_image_bytes_are_unchanged(monkeypatch):
    payload = b"\x89PNG\r\n" + FAKE_KEY.encode()

    def respond(method, url, **kwargs):
        if url.endswith(".json"):
            return httpx.Response(200, json={"attachment": {"filename": "image.png", "content_type": "image/png"}},
                                  request=httpx.Request(method, url))
        return httpx.Response(200, content=payload, request=httpx.Request(method, url))

    monkeypatch.setattr(server._http_client, "request", respond)
    result = server.redmine_attachment_image(1)
    assert isinstance(result, server.Image)
    assert result.data == payload


@pytest.mark.parametrize("name", ["httpx", "httpcore.http11", "mcp.server.mcpserver.server", server.__name__])
def test_diagnostic_logs_and_tracebacks_redacted(caplog, name):
    logger = logging.getLogger(name)
    with caplog.at_level(logging.DEBUG, logger=name):
        logger.info("request %s", quote(FAKE_KEY, safe=""))
        try:
            raise RuntimeError(f"api_key={OTHER_KEY}; {FAKE_KEY}")
        except RuntimeError:
            logger.exception("failure %s", FAKE_KEY)
    assert FAKE_KEY not in caplog.text and OTHER_KEY not in caplog.text
    assert quote(FAKE_KEY, safe="") not in caplog.text
    assert "RuntimeError" in caplog.text and REDACTED in caplog.text


def test_labelled_text_keeps_json_and_yaml_content(output_format):
    data = {"message": 'api_key="fake-another-key"; normal text', "name": "正常資料"}
    parsed = output_format(server.format_response(data))
    assert parsed == {"message": f'api_key="{REDACTED}"; normal text', "name": "正常資料"}


def test_secret_in_dictionary_key(output_format):
    parsed = output_format(server.format_response({FAKE_KEY: "ordinary"}))
    assert parsed == {REDACTED: "ordinary"}


def test_non_json_non_utf8_body(monkeypatch, output_format):
    mock_http(monkeypatch, content=b"\xff\x00api_key=" + OTHER_KEY.encode() + b"; normal")
    parsed = output_format(unwrap(server.redmine_request("issues.json")))
    assert OTHER_KEY not in str(parsed)
    if isinstance(parsed["body"], bytes):
        assert parsed["body"] == b"\xff\x00api_key=[REDACTED]; normal"


def test_path_validation_redacts_echoed_configured_key(monkeypatch, output_format, tmp_path):
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path])
    result = server.redmine_download(1, "/outside/" + FAKE_KEY)
    parsed = output_format(result)
    assert "not in allowed directories" in parsed["error"]
    assert FAKE_KEY not in result


def test_paths_tools_preserve_normal_spec(output_format):
    assert "/issues.json" in output_format(server.redmine_paths_list())
    parsed = output_format(server.redmine_paths_info(["/issues.json"]))
    assert parsed["/issues.json"]["get"]["operationId"] == server.SPEC["paths"]["/issues.json"]["get"]["operationId"]


def test_mcp_converted_tool_result(monkeypatch):
    import asyncio

    mock_http(monkeypatch, body={"user": {"id": 5, "api_key": OTHER_KEY}, "echo": FAKE_KEY})

    async def call():
        return await server.mcp.call_tool("redmine_request", {"path": "users/current.json"})

    result = asyncio.run(call())
    # Exercise the registered tool and MCP content conversion, beyond the Python function.
    text = str(result)
    assert OTHER_KEY not in text and FAKE_KEY not in text
    assert REDACTED in text


def test_real_httpx_log_uses_filter(monkeypatch, caplog):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    with httpx.Client(transport=transport) as client:
        monkeypatch.setattr(server, "_http_client", client)
        with caplog.at_level(logging.INFO, logger="httpx"):
            server.redmine_request("issues.json", params={"key": FAKE_KEY})
    assert "HTTP Request" in caplog.text
    assert FAKE_KEY not in caplog.text and quote(FAKE_KEY, safe="") not in caplog.text
    assert REDACTED in caplog.text


def test_read_only_upload_still_refused(monkeypatch, tmp_path, output_format):
    monkeypatch.setattr(server, "REDMINE_READ_ONLY", True)
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path])
    path = tmp_path / "file.txt"
    path.write_text("example")
    result = output_format(server.redmine_upload(str(path)))
    assert result["status_code"] == 0
    assert "REDMINE_READ_ONLY" in result["error"]


def test_subpath_traversal_and_filesystem_boundaries(monkeypatch, tmp_path, output_format):
    monkeypatch.setattr(server, "REDMINE_URL", "https://redmine.example.org/redmine/")
    monkeypatch.setattr(server, "REDMINE_ALLOWED_DIRECTORIES", [tmp_path / "allowed"])
    assert "escapes REDMINE_URL" in server.redmine_request("../issues.json")
    result = output_format(server.redmine_download(1, str(tmp_path / "allowed" / ".." / "outside.txt")))
    assert "not in allowed directories" in result["error"]
    assert not (tmp_path / "outside.txt").exists()


def test_schema_credential_response_paths():
    def contains_key(value, seen=frozenset()):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref and ref not in seen:
                target = server.SPEC
                for segment in ref.removeprefix("#/").split("/"):
                    target = target[segment]
                if contains_key(target, seen | {ref}):
                    return True
            return "api_key" in value or any(contains_key(v, seen) for v in value.values())
        return isinstance(value, list) and any(contains_key(v, seen) for v in value)

    paths = {(method, path) for path, operations in server.SPEC["paths"].items()
             for method, operation in operations.items()
             if isinstance(operation, dict) and contains_key(operation.get("responses", {}))}
    assert paths == {("get", "/users/current.json"), ("get", "/users/{user_id}.json"),
                     ("get", "/my/account.json"), ("post", "/users.json")}


def test_returned_key_echo_elsewhere_in_result(output_format):
    data = {"users": [{"api_key": OTHER_KEY}], "message": "echo " + OTHER_KEY,
            "error": quote(OTHER_KEY, safe="")}
    parsed = output_format(server.format_response(data))
    assert parsed == {"users": [{"api_key": REDACTED}], "message": "echo " + REDACTED,
                      "error": REDACTED}
