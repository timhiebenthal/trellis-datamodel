"""Tests for the local API's request hardening.

The API is unauthenticated and writes project files, so the server refuses
DNS-rebound Host headers, writes a foreign web page could have sent, and model
names that would turn into a path outside the models directory.
"""

import os

import httpx
import pytest
import yaml

from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.utils.path_validation import validate_model_name

VALIDATE_URL = "/api/config/validate"


@pytest.fixture(autouse=True)
def _loopback_bind(monkeypatch):
    """Every test starts as a default `trellis run` (loopback, no extra names)."""
    monkeypatch.setenv("TRELLIS_BIND_HOST", "127.0.0.1")
    monkeypatch.delenv("TRELLIS_ALLOWED_HOSTS", raising=False)


def _passed_guards(response) -> bool:
    return response.status_code not in (400, 403, 415)


class TestHostHeader:
    @pytest.mark.parametrize(
        "host", ["localhost", "localhost:8089", "127.0.0.1:8089", "[::1]:8089"]
    )
    def test_loopback_names_are_accepted(self, test_client, host):
        response = test_client.get("/health", headers={"host": host})

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "host", ["evil.example", "evil.example:8089", "192.168.1.20:8089", ""]
    )
    def test_rebound_or_foreign_names_are_rejected(self, test_client, host):
        response = test_client.get("/health", headers={"host": host})

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_testserver_is_only_accepted_from_the_test_client(self):
        """`testserver` passes for Starlette's TestClient, not for a real peer."""
        from trellis_datamodel.server import app

        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 400

    def test_wildcard_bind_accepts_ip_literals_but_not_names(
        self, test_client, monkeypatch
    ):
        monkeypatch.setenv("TRELLIS_BIND_HOST", "0.0.0.0")

        by_ip = test_client.get("/health", headers={"host": "192.168.1.20:8089"})
        by_v6 = test_client.get("/health", headers={"host": "[fe80::1]:8089"})
        rebound = test_client.get("/health", headers={"host": "evil.example:8089"})

        assert by_ip.status_code == 200
        assert by_v6.status_code == 200
        assert rebound.status_code == 400

    def test_specific_bind_host_name_is_accepted(self, test_client, monkeypatch):
        monkeypatch.setenv("TRELLIS_BIND_HOST", "devbox.lan")

        response = test_client.get("/health", headers={"host": "devbox.lan:8089"})

        assert response.status_code == 200

    def test_allowed_hosts_env_adds_names(self, test_client, monkeypatch):
        monkeypatch.setenv("TRELLIS_ALLOWED_HOSTS", "trellis.internal, other.lan")

        response = test_client.get("/health", headers={"host": "trellis.internal"})

        assert response.status_code == 200


class TestCrossSiteWrites:
    @pytest.mark.parametrize(
        "origin",
        ["http://localhost:5173", "http://127.0.0.1:8089", "http://[::1]:8089"],
    )
    def test_local_origin_json_write_is_accepted(self, test_client, origin):
        response = test_client.post(
            VALIDATE_URL, json={}, headers={"origin": origin}
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin

    def test_write_without_origin_is_accepted(self, test_client):
        """curl, scripts and the CLI send no Origin."""
        response = test_client.post(VALIDATE_URL, json={})

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "origin", ["https://evil.example", "http://localhost.evil.example", "null"]
    )
    def test_foreign_origin_write_is_rejected(self, test_client, origin):
        response = test_client.post(
            VALIDATE_URL, json={}, headers={"origin": origin}
        )

        assert response.status_code == 403
        assert "access-control-allow-origin" not in response.headers

    @pytest.mark.parametrize(
        "method, url",
        [
            ("post", "/api/config/reload"),
            ("post", "/api/sync-tests"),
            ("post", "/api/reconcile"),
            ("put", "/api/config"),
            ("delete", "/api/business-events/anything"),
        ],
    )
    def test_foreign_origin_is_rejected_on_every_mutating_method(
        self, test_client, method, url
    ):
        response = test_client.request(
            method, url, headers={"origin": "https://evil.example"}
        )

        assert response.status_code == 403

    def test_foreign_origin_read_is_not_blocked(self, test_client):
        """Reads are protected by CORS hiding the response, not by refusal."""
        response = test_client.get(
            "/health", headers={"origin": "https://evil.example"}
        )

        assert response.status_code == 200

    def test_rejected_write_never_reaches_the_handler(self, test_client, temp_dir):
        """A no-cors `fetch` with a JSON Blob body: no Content-Type, no preflight."""
        target = os.path.join(temp_dir, "models", "csrf_probe.yml")

        response = test_client.post(
            "/api/schema",
            content=b'{"entity_id": "csrf_probe", "model_name": "csrf_probe", "fields": []}',
            headers={"origin": "https://evil.example"},
        )

        assert response.status_code == 403
        assert not os.path.exists(target)

    def test_cross_site_fetch_metadata_is_rejected(self, test_client):
        response = test_client.post(
            VALIDATE_URL, json={}, headers={"sec-fetch-site": "cross-site"}
        )

        assert response.status_code == 403

    @pytest.mark.parametrize("site", ["same-origin", "same-site", "none"])
    def test_same_site_fetch_metadata_is_accepted(self, test_client, site):
        response = test_client.post(
            VALIDATE_URL, json={}, headers={"sec-fetch-site": site}
        )

        assert response.status_code == 200

    def test_local_origin_wins_over_cross_site_fetch_metadata(self, test_client):
        """A page on localhost calling 127.0.0.1 is labelled cross-site."""
        response = test_client.post(
            VALIDATE_URL,
            json={},
            headers={
                "origin": "http://localhost:5173",
                "sec-fetch-site": "cross-site",
            },
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "content_type", ["text/plain", "application/x-www-form-urlencoded", None]
    )
    def test_non_json_body_is_rejected(self, test_client, content_type):
        headers = {"content-type": content_type} if content_type else {}

        response = test_client.post(VALIDATE_URL, content=b"{}", headers=headers)

        assert response.status_code == 415

    def test_non_json_body_from_local_origin_is_still_rejected(self, test_client):
        response = test_client.post(
            VALIDATE_URL,
            content=b"{}",
            headers={"origin": "http://localhost:5173", "content-type": "text/plain"},
        )

        assert response.status_code == 415
        # CORS still decorates the rejection so the UI can read the reason.
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_json_with_charset_is_accepted(self, test_client):
        response = test_client.post(
            VALIDATE_URL,
            content=b"{}",
            headers={"content-type": "application/json; charset=utf-8"},
        )

        assert response.status_code == 200

    def test_bodyless_post_without_content_type_passes_the_guard(self, test_client):
        """`/api/config/reload`, `/api/reconcile` and friends send no body."""
        response = test_client.post(VALIDATE_URL)

        # FastAPI's own missing-body 422, i.e. the request reached routing.
        assert response.status_code == 422

    def test_network_bind_ui_same_origin_write_is_accepted(
        self, test_client, monkeypatch
    ):
        """The bundled UI over an opted-in bind sends its own address as Origin."""
        monkeypatch.setenv("TRELLIS_BIND_HOST", "0.0.0.0")
        host = "192.168.1.20:8089"

        own = test_client.post(
            VALIDATE_URL,
            json={},
            headers={"host": host, "origin": f"http://{host}"},
        )
        other = test_client.post(
            VALIDATE_URL,
            json={},
            headers={"host": host, "origin": "http://192.168.1.21:8089"},
        )

        assert own.status_code == 200
        assert other.status_code == 403


class TestModelNameValidation:
    @pytest.mark.parametrize(
        "name", ["users", "dim__customer", "core.dim__customer", "player.v2", "my-model"]
    )
    def test_accepts_dbt_and_bruin_names(self, name):
        assert validate_model_name(name) == name

    @pytest.mark.parametrize(
        "name",
        ["", "../escape", "a/b", "a\\b", "..", "sub..name", ".hidden", "/etc/x", "a b"],
    )
    def test_rejects_names_that_are_not_plain_file_names(self, name):
        with pytest.raises(ValidationError):
            validate_model_name(name)

    @pytest.mark.parametrize("model_name", ["../escape", "../../tmp/escape", "a/b"])
    def test_post_schema_rejects_traversing_model_name(
        self, test_client, temp_dir, model_name
    ):
        response = test_client.post(
            "/api/schema",
            json={
                "entity_id": "not_in_data_model",
                "model_name": model_name,
                "fields": [{"name": "id", "datatype": "int"}],
            },
        )

        assert response.status_code == 422
        assert "Invalid model name" in response.json()["detail"]
        assert not os.path.exists(os.path.join(temp_dir, "escape.yml"))

    def test_post_model_schema_rejects_invalid_path_name(self, test_client):
        response = test_client.post(
            "/api/models/sub..name/schema", json={"columns": [{"name": "id"}]}
        )

        assert response.status_code == 422

    def test_post_schema_with_plain_name_still_writes(self, test_client):
        response = test_client.post(
            "/api/schema",
            json={
                "entity_id": "hardening_ok",
                "model_name": "hardening_ok",
                "fields": [{"name": "id", "datatype": "int"}],
            },
        )

        assert response.status_code == 200
        assert response.json()["file_path"].endswith("hardening_ok.yml")


class TestSchemaWriteContainment:
    """Entity ids from data_model.yml skip the route check, so the write site
    refuses on its own a default schema path that leaves the models directory."""

    def test_default_path_helper_refuses_escape(self, tmp_path):
        from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter

        models_dir = str(tmp_path / "models")

        with pytest.raises(ValidationError):
            DbtCoreAdapter._default_schema_yml_path(models_dir, "../escape")
        assert DbtCoreAdapter._default_schema_yml_path(models_dir, "ok") == (
            os.path.join(models_dir, "ok.yml")
        )

    def test_sync_tests_refuses_entity_id_that_escapes(
        self, test_client, temp_dir, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            yaml.dump(
                {
                    "version": 0.1,
                    "entities": [{"id": "../sync_escape", "label": "Escape"}],
                    "relationships": [],
                },
                f,
            )

        response = test_client.post("/api/sync-tests")

        assert response.status_code == 422
        assert not os.path.exists(os.path.join(temp_dir, "sync_escape.yml"))
