"""Never inherit a developer's real Redmine configuration in tests."""
import os

for name in list(os.environ):
    if name.startswith("REDMINE_"):
        del os.environ[name]
os.environ["REDMINE_URL"] = "https://redmine.example.org"
os.environ["REDMINE_API_KEY"] = "test-api-key-123"

import pytest


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch):
    from mcp_redmine import server

    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must mock HTTP; real requests are forbidden")

    monkeypatch.setattr(server._http_client, "request", forbidden)
