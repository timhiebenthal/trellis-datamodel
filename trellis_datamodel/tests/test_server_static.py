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

