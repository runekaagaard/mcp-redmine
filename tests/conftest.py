import os
import subprocess

import pytest

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.test.yml")
REDMINE_PORT = 3123
REDMINE_BASE_URL = f"http://localhost:{REDMINE_PORT}"


def _setup_redmine():
    """Load default data, enable REST API, create API token, and create test project.

    Returns the API key for the admin user.
    """
    rails_script = (
        "Redmine::DefaultData::Loader.load('en') unless Tracker.any?; "
        "Setting.rest_api_enabled = '1'; "
        "token = Token.create!(user_id: 1, action: 'api'); "
        "Project.create!(name: 'Test', identifier: 'test') unless Project.exists?(identifier: 'test'); "
        "puts token.value"
    )
    result = subprocess.run(
        [
            "docker", "compose", "-f", COMPOSE_FILE,
            "exec", "-T", "redmine",
            "bundle", "exec", "rails", "runner", rails_script,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    # Rails may emit log lines before the token; take only the last line.
    return result.stdout.strip().splitlines()[-1].strip()


@pytest.fixture(scope="session")
def redmine_service():
    """Start Redmine via Docker Compose, wait for readiness, and tear down after."""
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "--wait", "--wait-timeout", "180"],
        check=True,
    )
    try:
        api_key = _setup_redmine()
        yield {"url": REDMINE_BASE_URL, "api_key": api_key}
    finally:
        subprocess.run(
            ["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"],
            check=True,
        )


@pytest.fixture(scope="session")
def server(redmine_service):
    """Import mcp_redmine.server after env vars are configured."""
    os.environ["REDMINE_URL"] = redmine_service["url"]
    os.environ["REDMINE_API_KEY"] = redmine_service["api_key"]
    os.environ.pop("REDMINE_READ_ONLY", None)

    import mcp_redmine.server as srv

    # Ensure module-level constants match (they're read at import time)
    srv.REDMINE_URL = redmine_service["url"].rstrip("/") + "/"
    srv.REDMINE_API_KEY = redmine_service["api_key"]
    srv.REDMINE_READ_ONLY = False

    return srv


@pytest.fixture()
def read_only(server, monkeypatch):
    """Enable read-only mode for the duration of a test."""
    monkeypatch.setattr(server, "REDMINE_READ_ONLY", True)
