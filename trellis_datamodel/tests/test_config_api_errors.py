"""Error-path tests for the config API (/api/config)."""

import os
import textwrap

import pytest
from starlette.testclient import TestClient

VALID_CONFIG = textwrap.dedent(
    """\
    framework: dbt-core
    dbt_project_path: ./dbt_project
    data_model_file: data_model.yml
    """
)


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """A project dir whose trellis.yml the server discovers via the environment."""
    path = tmp_path / "trellis.yml"
    path.write_text(VALID_CONFIG)
    (tmp_path / "dbt_project").mkdir()
    monkeypatch.setenv("TRELLIS_CONFIG_PATH", str(path))
    monkeypatch.chdir(tmp_path)
    return path


@pytest.fixture
def no_config(tmp_path, monkeypatch):
    """An empty cwd with no config discoverable anywhere."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.delenv("TRELLIS_CONFIG_PATH", raising=False)
    monkeypatch.chdir(empty)


@pytest.fixture
def client():
    # Other config tests reload these modules with a patched find_config_file
    # and leave the patched binding behind; rebind to the real lookup.
    import importlib
    import sys

    for name in ("trellis_datamodel.routes.config", "trellis_datamodel.server"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    from trellis_datamodel.server import app

    with TestClient(app, base_url="http://localhost") as c:
        yield c


def test_get_config_without_config_file_reports_error_and_still_serves_schema(
    client, no_config
):
    response = client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["config"] == {}
    assert body["file_info"] is None
    assert "No config file found" in body["error"]
    assert "fields" in body["schema_metadata"]


def test_get_config_with_unparseable_yaml_reports_read_failure(client, config_file):
    config_file.write_text("framework: [unclosed\n")

    response = client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["config"] == {}
    assert body["error"].startswith("Failed to read config file")


def test_get_config_with_non_mapping_yaml_returns_500(client, config_file):
    config_file.write_text("- just\n- a list\n")

    response = client.get("/api/config")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to load configuration"


def test_put_config_without_config_file_returns_400_configuration_error(
    client, no_config
):
    response = client.put("/api/config", json={"config": {"framework": "dbt-core"}})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "configuration_error"
    assert "No config file found" in detail["message"]


@pytest.mark.xfail(
    strict=True,
    reason="POST /api/config/reload answers 200 'success' when trellis.yml is "
    "unparseable: config.load_config only logs a warning and keeps stale values",
)
def test_reload_config_with_unparseable_yaml_returns_400(client, config_file):
    config_file.write_text("framework: [unclosed\n")

    response = client.post("/api/config/reload")

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "configuration_error"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_put_config_when_config_file_cannot_be_written_returns_500(
    client, config_file
):
    config_file.chmod(0o444)
    config_file.parent.chmod(0o555)
    try:
        response = client.put(
            "/api/config",
            json={"config": {"framework": "dbt-core", "dbt_project_path": "./dbt_project"}},
        )
    finally:
        config_file.parent.chmod(0o755)
        config_file.chmod(0o644)

    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "internal_error"
