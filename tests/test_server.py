"""Tests for mcp_redmine.server. Run with: make tests-run"""
import os

# Server module reads config from environment at import time
os.environ.setdefault("REDMINE_URL", "https://redmine.example.org")
os.environ.setdefault("REDMINE_API_KEY", "test-api-key-123")

import pytest

from mcp_redmine import server


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, content=b""):
        self.status_code = status_code
        self._json_body = json_body
        self.content = content if not json_body else b"x"

    def raise_for_status(self):
        pass

    def json(self):
        if self._json_body is None:
            raise ValueError("no json")
        return self._json_body


@pytest.fixture
def capture_requests(monkeypatch):
    """Capture outgoing requests instead of hitting the network."""
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse(json_body={"ok": True})

    monkeypatch.setattr(server._http_client, "request", fake_request)
    return calls


# Security: model-controlled `path` must never escape REDMINE_URL (issue #44)

def test_normal_path_stays_on_redmine(capture_requests):
    result = server.request("issues.json")
    assert result["status_code"] == 200
    assert capture_requests[0]["url"] == "https://redmine.example.org/issues.json"


def test_leading_slash_path_stays_on_redmine(capture_requests):
    server.request("/issues.json")
    assert capture_requests[0]["url"] == "https://redmine.example.org/issues.json"


@pytest.mark.parametrize("path", [
    "https://attacker.example/collect",
    "http://attacker.example/collect",
    "https://redmine.example.org.attacker.example/collect",
    "ftp://attacker.example/collect",
])
def test_escaping_paths_are_refused(capture_requests, path):
    result = server.request(path)
    assert result["status_code"] == 0
    assert "escapes REDMINE_URL" in result["error"]
    assert capture_requests == []  # nothing left the building


@pytest.mark.parametrize("path", [
    "//attacker.example/collect",  # neutralized by lstrip('/')
    "../../../collect",  # dot segments resolved by urljoin, can't climb above the host
    "/../collect",
])
def test_tricky_paths_stay_on_redmine_host(capture_requests, path):
    server.request(path)
    assert len(capture_requests) == 1
    assert capture_requests[0]["url"].startswith("https://redmine.example.org/")


def test_api_key_only_sent_to_redmine(capture_requests):
    server.request("issues.json")
    assert capture_requests[0]["headers"]["X-Redmine-API-Key"] == "test-api-key-123"


# Read-only mode (REDMINE_READ_ONLY)

def test_read_only_blocks_writes(capture_requests, monkeypatch):
    monkeypatch.setattr(server, "REDMINE_READ_ONLY", True)
    for method in ["post", "put", "PATCH", "delete"]:
        result = server.request("issues.json", method=method)
        assert result["status_code"] == 0
        assert "REDMINE_READ_ONLY" in result["error"]
    assert capture_requests == []


def test_read_only_allows_get(capture_requests, monkeypatch):
    monkeypatch.setattr(server, "REDMINE_READ_ONLY", True)
    result = server.request("issues.json", method="get")
    assert result["status_code"] == 200
    assert len(capture_requests) == 1


def test_writes_allowed_by_default(capture_requests):
    result = server.request("issues.json", method="post", data={"issue": {}})
    assert result["status_code"] == 200


# Tool plumbing

def test_redmine_request_tool_wraps_insecure_content(capture_requests):
    result = server.redmine_request("issues.json")
    assert "<insecure-content-" in result
    assert "status_code: 200" in result


def test_paths_list_returns_spec_paths():
    result = server.format_response(list(server.SPEC["paths"].keys()))
    assert "/issues.json" in result


def test_attachment_image_rejects_non_image(monkeypatch):
    def fake_request(path, method="get", **kwargs):
        return {"status_code": 200, "error": "",
                "body": {"attachment": {"content_type": "application/pdf", "filename": "a.pdf", "filesize": 10}}}

    monkeypatch.setattr(server, "request", fake_request)
    result = server.redmine_attachment_image(1)
    assert isinstance(result, str) and "not an image" in result


def test_attachment_image_rejects_oversize(monkeypatch):
    def fake_request(path, method="get", **kwargs):
        return {"status_code": 200, "error": "",
                "body": {"attachment": {"content_type": "image/png", "filename": "a.png",
                                        "filesize": server.ATTACHMENT_IMAGE_MAX_BYTES + 1}}}

    monkeypatch.setattr(server, "request", fake_request)
    result = server.redmine_attachment_image(1)
    assert isinstance(result, str) and "too large" in result


def test_attachment_image_returns_image(monkeypatch):
    png_bytes = b"\x89PNG\r\n\x1a\nfakepngdata"

    def fake_request(path, method="get", **kwargs):
        if path.endswith(".json"):
            return {"status_code": 200, "error": "",
                    "body": {"attachment": {"content_type": "image/png", "filename": "a.png", "filesize": 20}}}
        return {"status_code": 200, "error": "", "body": png_bytes}

    monkeypatch.setattr(server, "request", fake_request)
    result = server.redmine_attachment_image(1)
    assert isinstance(result, server.Image)
