"""Integration tests for REDMINE_READ_ONLY mode."""

import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(response_str: str) -> dict:
    """Parse a YAML/JSON response string from a tool function.

    The response may be wrapped in <insecure-content-*> tags so we strip those
    before parsing.
    """
    # Strip wrapping tags if present
    lines = response_str.strip().splitlines()
    if lines and lines[0].startswith("<insecure-content-"):
        lines = lines[1:]
    if lines and lines[-1].startswith("</insecure-content-"):
        lines = lines[:-1]
    return yaml.safe_load("\n".join(lines))


# ---------------------------------------------------------------------------
# Read-only ON — write operations blocked
# ---------------------------------------------------------------------------


class TestReadOnlyWritesBlocked:
    """Verify that all write operations are blocked when REDMINE_READ_ONLY=1.

    Covers POST, PUT, DELETE, PATCH via redmine_request and file uploads
    via redmine_upload. GET requests should still be allowed.
    """

    def test_get_request_allowed(self, server, read_only):
        result = _parse(server.redmine_request("/projects.json"))
        assert result["status_code"] == 200
        assert result["body"] is not None

    def test_post_blocked(self, server, read_only):
        result = _parse(
            server.redmine_request(
                "/issues.json",
                method="post",
                data={"issue": {"project_id": 1, "subject": "blocked"}},
            )
        )
        assert result["error"]
        assert result["status_code"] == 0

    def test_put_blocked(self, server, read_only):
        result = _parse(
            server.redmine_request(
                "/issues/1.json",
                method="put",
                data={"issue": {"subject": "blocked"}},
            )
        )
        assert result["error"]
        assert result["status_code"] == 0

    def test_delete_blocked(self, server, read_only):
        result = _parse(
            server.redmine_request("/issues/1.json", method="delete")
        )
        assert result["error"]
        assert result["status_code"] == 0

    def test_patch_blocked(self, server, read_only):
        result = _parse(
            server.redmine_request(
                "/issues/1.json",
                method="patch",
                data={"issue": {"subject": "blocked"}},
            )
        )
        assert result["error"]
        assert result["status_code"] == 0

    def test_upload_blocked(self, server, read_only):
        result = _parse(server.redmine_upload("/any/path"))
        assert result["error"]
        assert result["status_code"] == 0


# ---------------------------------------------------------------------------
# Read-only ON — read operations still work
# ---------------------------------------------------------------------------


class TestReadOnlyReadsWork:
    """Verify that read-only operations still work when REDMINE_READ_ONLY=1.

    Covers redmine_paths_list, redmine_paths_info, and redmine_download.
    These should never be blocked by read-only mode.
    """

    def test_paths_list_works(self, server, read_only):
        result = yaml.safe_load(server.redmine_paths_list())
        assert isinstance(result, list)
        assert len(result) > 0

    def test_paths_info_works(self, server, read_only):
        result = yaml.safe_load(
            server.redmine_paths_info(["/issues.json"])
        )
        assert "/issues.json" in result

    def test_download_not_blocked(self, server, read_only):
        """redmine_download is a read operation and must not be blocked."""
        result = _parse(server.redmine_download(1, "/tmp/test.txt"))
        # May fail for other reasons (e.g. ALLOWED_DIRECTORIES not set),
        # but must never be blocked by read-only mode.
        assert "REDMINE_READ_ONLY" not in result.get("error", "")


# ---------------------------------------------------------------------------
# Read-only OFF — write operations work
# ---------------------------------------------------------------------------


class TestWriteOperationsAllowed:
    """Verify that write operations succeed when REDMINE_READ_ONLY is not set.

    These tests do NOT use the read_only fixture, so the server operates
    in its default (read-write) mode against the live Redmine instance.
    """

    def test_post_allowed(self, server):
        result = _parse(
            server.redmine_request(
                "/issues.json",
                method="post",
                data={
                    "issue": {
                        "project_id": "test",
                        "subject": "Integration test issue",
                    }
                },
            )
        )
        assert result["status_code"] == 201, f"Unexpected response: {result}"
        assert result["body"]["issue"]["id"]

    def test_put_allowed(self, server):
        # First create an issue to update
        create_result = _parse(
            server.redmine_request(
                "/issues.json",
                method="post",
                data={
                    "issue": {
                        "project_id": "test",
                        "subject": "Issue to update",
                    }
                },
            )
        )
        issue_id = create_result["body"]["issue"]["id"]

        # Now update it
        update_result = _parse(
            server.redmine_request(
                f"/issues/{issue_id}.json",
                method="put",
                data={"issue": {"subject": "Updated subject"}},
            )
        )
        assert update_result["status_code"] in (200, 204), (
            f"Unexpected response: {update_result}"
        )


# ---------------------------------------------------------------------------
# Error message format
# ---------------------------------------------------------------------------


class TestErrorMessageFormat:
    """Verify that read-only error messages include actionable information.

    The error should mention the blocked HTTP method and the environment
    variable (REDMINE_READ_ONLY=1) so users know how to disable the restriction.
    """

    def test_error_message_contains_method(self, server, read_only):
        result = _parse(
            server.redmine_request("/issues.json", method="post", data={})
        )
        assert "POST" in result["error"]

    def test_error_message_contains_env_var(self, server, read_only):
        result = _parse(
            server.redmine_request("/issues.json", method="post", data={})
        )
        assert "REDMINE_READ_ONLY=1" in result["error"]
