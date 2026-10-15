import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_frontend_build(tmp_path, monkeypatch):
    """
    Create a minimal frontend build directory and point config to it.
    """
    build_dir: Path = tmp_path / "frontend" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    index_file = build_dir / "index.html"
    index_file.write_text("<html><body>Hello Test Build</body></html>")

    # Force test-mode paths and override frontend build dir
    monkeypatch.setenv("DATAMODEL_TEST_DIR", str(tmp_path))
    monkeypatch.setenv("DATAMODEL_FRONTEND_BUILD_DIR", str(build_dir))

    return build_dir


def test_serves_frontend_build_when_present(temp_frontend_build):
    """
    Ensure the server serves index.html from the configured frontend build dir.
    """
    # Reload config/server to pick up env overrides
    import trellis_datamodel.config as cfg
    import trellis_datamodel.server as srv

    importlib.reload(cfg)
    cfg.load_config(None)
    importlib.reload(srv)

    app = srv.create_app()
    client = TestClient(app)

    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Hello Test Build" in resp.content


def test_startup_loads_config_when_not_preloaded(tmp_path, monkeypatch):
    """
    Regression test for issue #136: serving the app directly (bypassing the CLI)
    must apply trellis.yml at startup. Drives the real lifespan hook via
    TestClient's context manager, and uses a framework value that differs from
    the default so the assertions cannot pass with the hook removed.
    """
    import trellis_datamodel.config as cfg
    from trellis_datamodel.server import app

    # Simulate a fresh uvicorn worker: nothing pre-loaded, not in test mode
    monkeypatch.delenv("DATAMODEL_TEST_DIR", raising=False)
    monkeypatch.setattr(cfg, "_TEST_DIR", "")
    monkeypatch.setattr(cfg, "CONFIG_PATH", "")
    monkeypatch.setattr(cfg, "FRAMEWORK", "dbt-core")

    config_file = tmp_path / "trellis.yml"
    config_file.write_text("framework: bruin\n")
    monkeypatch.setenv("TRELLIS_CONFIG_PATH", str(config_file))

    # Entering the TestClient context sends ASGI startup -> runs lifespan()
    with TestClient(app):
        assert cfg.FRAMEWORK == "bruin"
        assert cfg.CONFIG_PATH == str(config_file)

