"""Tests for lineage endpoints."""

import pytest

from trellis_datamodel import config as cfg


@pytest.mark.anyio(specific_backend="asyncio")
async def test_lineage_returns_forbidden_when_disabled(test_client):
    cfg.LINEAGE_ENABLED = False

    response = await test_client.get("/api/lineage/model.project.users")

    assert response.status_code == 403
    assert "Lineage is disabled" in response.json()["detail"]


@pytest.mark.anyio(specific_backend="asyncio")
async def test_lineage_succeeds_when_enabled(monkeypatch, test_client):
    monkeypatch.setattr(cfg, "LINEAGE_ENABLED", True)

    response = await test_client.get("/api/lineage/model.project.users")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "metadata" in data
