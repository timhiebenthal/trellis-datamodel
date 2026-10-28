"""
Trellis Data - FastAPI Server

This is the FastAPI application that serves the API and frontend.
"""

from importlib.resources import files
import ipaddress
import logging
import os
import re
import socket
from contextlib import asynccontextmanager
from functools import lru_cache
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from trellis_datamodel import config as cfg
from trellis_datamodel.config import load_config, find_config_file
from trellis_datamodel.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError,
    ConfigurationError,
    FileOperationError,
    FeatureDisabledError,
)
from trellis_datamodel.observability import (
    PhaseCollector,
    reset_collector,
    serialize_server_timing,
    set_collector,
)
from trellis_datamodel.routes import (
    bus_matrix_router,
    business_events_router,
    config_router,
    data_model_router,
    exposures_router,
    lineage_router,
    manifest_router,
    metric_tree_router,
    reconcile_router,
    schema_router,
)

logger = logging.getLogger(__name__)


class _RequestTimingMiddleware:
    """Attach safe request timing metadata to every HTTP response."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        collector = PhaseCollector()
        collector_token = set_collector(collector)
        started_at = perf_counter()
        response_started = False
        total_recorded = False

        def record_total_request() -> None:
            nonlocal total_recorded
            if not total_recorded:
                collector.add("request", (perf_counter() - started_at) * 1000)
                total_recorded = True

        async def send_with_headers(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                record_total_request()
                response_started = True
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower()
                    not in {b"server-timing", b"x-trellis-request-id"}
                ]
                headers.append((b"x-trellis-request-id", request_id.encode("ascii")))
                headers.append(
                    (
                        b"server-timing",
                        serialize_server_timing(collector).encode("ascii"),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            record_total_request()
            if not response_started:
                error_response = PlainTextResponse("Internal Server Error", status_code=500)
                await error_response(scope, receive, send_with_headers)
            raise
        finally:
            reset_collector(collector_token)


# The API is unauthenticated and writes project files, so only pages served from
# this machine (the bundled UI, or the Vite dev server on any port) may call it
# cross-origin. There are no cookies, so credentials stay off.
_LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
_LOCAL_ORIGIN_PATTERN = re.compile(_LOCAL_ORIGIN_REGEX)

_LOOPBACK_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "[::1]"})
_LOOPBACK_BIND_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Starlette's TestClient always reports this peer and sends `Host: testserver`.
# A real socket peer is an IP address, so matching the exact tuple lets the test
# client through without accepting `testserver` from the network.
_STARLETTE_TEST_CLIENT = ("testclient", 50000)


def _is_local_origin(origin: str) -> bool:
    """Whether *origin* is a page served from this machine (same rule as CORS)."""
    return _LOCAL_ORIGIN_PATTERN.fullmatch(origin) is not None


def _host_without_port(host: str) -> str:
    """`localhost:8089` -> `localhost`, `[::1]:8089` -> `[::1]`."""
    host = host.strip().lower()
    if host.startswith("["):
        end = host.find("]")
        return host[: end + 1] if end != -1 else host
    return host.rsplit(":", 1)[0] if ":" in host else host


def _is_ip_literal(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname.strip("[]"))
    except ValueError:
        return False
    return True


@lru_cache(maxsize=8)
def _allowed_hostnames(bind_host: str, extra_hosts: str) -> tuple[frozenset, bool]:
    """Host header names the server answers to, and whether any IP literal is OK.

    `trellis run` binds loopback by default, so only loopback names are valid
    and a DNS-rebound name (`evil.example` resolving to 127.0.0.1) is refused.
    An explicit non-loopback `--host` is an opt-in to being reached over the
    network, so the bind address, this machine's names and any IP literal are
    accepted too: rebinding needs an attacker-controlled *name*, never an IP.
    `TRELLIS_ALLOWED_HOSTS` (comma-separated) adds names such as a proxy's.
    """
    names = set(_LOOPBACK_HOSTNAMES)
    names.update(
        h.strip().lower() for h in extra_hosts.split(",") if h.strip()
    )
    if not bind_host or bind_host in _LOOPBACK_BIND_HOSTS:
        return frozenset(names), False

    if ":" in bind_host and not bind_host.startswith("["):
        names.add(f"[{bind_host.lower()}]")
    else:
        names.add(bind_host.lower())
    try:
        hostname = socket.gethostname()
        names.update({hostname.lower(), f"{hostname.lower()}.local"})
        names.add(socket.getfqdn().lower())
    except OSError:
        pass
    return frozenset(names), True


def _is_allowed_host(host: str) -> bool:
    names, any_ip = _allowed_hostnames(
        os.environ.get("TRELLIS_BIND_HOST", ""),
        os.environ.get("TRELLIS_ALLOWED_HOSTS", ""),
    )
    hostname = _host_without_port(host)
    return hostname in names or (any_ip and _is_ip_literal(hostname))


def _header(scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class _TrustedHostMiddleware:
    """Refuse requests whose Host header is not a name this server answers to.

    Without this, a page on `evil.example` can rebind its DNS to 127.0.0.1 and
    then read and write the API as a same-origin caller, sidestepping CORS.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        host = _header(scope, b"host") or ""
        is_test_client = tuple(scope.get("client") or ()) == _STARLETTE_TEST_CLIENT
        if not (_is_allowed_host(host) or (is_test_client and host == "testserver")):
            response = PlainTextResponse("Invalid host header", status_code=400)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class _CrossSiteWriteGuardMiddleware:
    """Refuse state-changing requests a foreign web page could have sent.

    CORS only hides responses; a "simple" cross-site POST (no-cors fetch, form
    post) still reaches the handler. FastAPI parses a body without a JSON
    Content-Type as JSON anyway, so a page could rewrite project files without
    ever triggering a preflight. Every write the UI makes is JSON from a local
    origin, so anything else is refused before routing. Callers that send no
    Origin (curl, scripts, tests) are not browsers acting for a page and pass.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in _MUTATING_METHODS:
            await self.app(scope, receive, send)
            return

        rejection = self._rejection(scope)
        if rejection is not None:
            await rejection(scope, receive, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _rejection(scope) -> JSONResponse | None:
        origin = _header(scope, b"origin")
        host = _header(scope, b"host") or ""
        # The bundled UI reached over an opted-in network bind sends its own
        # address as Origin; the Host check has already vetted that address.
        trusted_origin = origin is not None and (
            _is_local_origin(origin)
            or origin.split("://", 1)[-1].lower() == host.strip().lower()
        )
        if origin is not None and not trusted_origin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin write refused", "error": "forbidden"},
            )

        # Browsers that strip Origin still label the request. A local page on
        # another loopback name (localhost vs 127.0.0.1) is "cross-site" too, so
        # a trusted Origin takes precedence.
        fetch_site = (_header(scope, b"sec-fetch-site") or "").lower()
        if fetch_site == "cross-site" and not trusted_origin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-site write refused", "error": "forbidden"},
            )

        content_length = _header(scope, b"content-length")
        has_body = _header(scope, b"transfer-encoding") is not None or (
            content_length is not None and content_length.strip() not in ("", "0")
        )
        content_type = (_header(scope, b"content-type") or "").split(";", 1)[0]
        if has_body and content_type.strip().lower() != "application/json":
            return JSONResponse(
                status_code=415,
                content={
                    "detail": "Request body must be application/json",
                    "error": "unsupported_media_type",
                },
            )
        return None


def _configure_cors(app: FastAPI) -> None:
    """Allow cross-origin calls from localhost pages only."""
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=_LOCAL_ORIGIN_REGEX,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _discover_static_dir() -> str | None:
    """
    Resolve static directory to serve frontend assets.

    Priority: configured FRONTEND_BUILD_DIR, then packaged static dir with index.html.
    """
    static_dir_path = None

    if cfg.FRONTEND_BUILD_DIR and os.path.exists(
        os.path.join(cfg.FRONTEND_BUILD_DIR, "index.html")
    ):
        static_dir_path = cfg.FRONTEND_BUILD_DIR
    else:
        try:
            static_dir = files("trellis_datamodel") / "static"
            if static_dir.is_dir():
                pkg_index = str(static_dir / "index.html")
                if os.path.exists(pkg_index):
                    static_dir_path = str(static_dir)
        except Exception:
            pass

    return static_dir_path


def _mount_static_routes(app: FastAPI, static_dir_path: str) -> None:
    """Mount static assets and SPA fallback routes."""
    assets_path = os.path.join(static_dir_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    app_path = os.path.join(static_dir_path, "_app")
    if os.path.exists(app_path):
        app.mount("/_app", StaticFiles(directory=app_path), name="app")

    # Serve SvelteKit data files (e.g., __data.json) before catch-all SPA route
    @app.get("/__data.json", include_in_schema=False)
    async def serve_data_json():
        """Serve SvelteKit __data.json file."""
        data_file = os.path.join(static_dir_path, "__data.json")
        if os.path.exists(data_file):
            return FileResponse(data_file, media_type="application/json")
        raise HTTPException(status_code=404, detail="Not found")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        """Serve SPA index.html for non-API routes."""
        index_file = os.path.join(static_dir_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not found")


def _register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for domain exceptions."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        """Handle NotFoundError -> 404."""
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message, "error": "not_found"},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        """Handle ValidationError -> 422."""
        return JSONResponse(
            status_code=422,
            content={"detail": exc.message, "error": "validation_error"},
        )

    @app.exception_handler(FeatureDisabledError)
    async def feature_disabled_handler(request: Request, exc: FeatureDisabledError):
        """Handle FeatureDisabledError -> 403."""
        return JSONResponse(
            status_code=403,
            content={"detail": exc.message, "error": "feature_disabled"},
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_handler(request: Request, exc: ConfigurationError):
        """Handle ConfigurationError -> 400."""
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message, "error": "configuration_error"},
        )

    @app.exception_handler(FileOperationError)
    async def file_operation_handler(request: Request, exc: FileOperationError):
        """Handle FileOperationError -> 500."""
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message, "error": "file_operation_error"},
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        """Handle generic DomainError -> 500."""
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message, "error": "domain_error"},
        )


def _register_routers(app: FastAPI) -> None:
    """Register API routers before mounting static files."""
    app.include_router(config_router)
    app.include_router(manifest_router)
    app.include_router(data_model_router)
    app.include_router(schema_router)
    app.include_router(reconcile_router)
    app.include_router(exposures_router)
    app.include_router(lineage_router)
    app.include_router(bus_matrix_router)
    app.include_router(business_events_router)
    app.include_router(metric_tree_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load configuration at startup if not already loaded."""
    # Skip if config already loaded (CLI path) or in test mode
    if not cfg.CONFIG_PATH and not os.environ.get("DATAMODEL_TEST_DIR"):
        config_path = find_config_file()
        if config_path:
            load_config(config_path)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Trellis Data", version="0.1.0", lifespan=lifespan)

    # The last middleware added runs first: the Host check precedes the write
    # guard, and CORS wraps both so a local page can still read their rejections.
    app.add_middleware(_CrossSiteWriteGuardMiddleware)
    app.add_middleware(_TrustedHostMiddleware)
    _configure_cors(app)
    app.add_middleware(_RequestTimingMiddleware)
    _register_exception_handlers(app)

    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "ok"}


    # Favicon endpoint - serves trellis_squared.svg
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        # Serve the trellis_squared.svg as favicon (browsers accept SVG)
        favicon_path = os.path.join(
            os.path.dirname(__file__), "static/trellis_squared.svg"
        )
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path, media_type="image/svg+xml")
        # Fallback to 204 if file doesn't exist
        return Response(status_code=204)

    static_dir_path = _discover_static_dir()

    logger.info("Serving frontend from: %s", static_dir_path)

    _register_routers(app)

    # Mount static files AFTER API routes
    # Important: app.mount() creates a sub-application, so we mount AFTER registering API routes
    # However, mounted apps at "/" will intercept everything, so we need a different approach
    if static_dir_path:
        _mount_static_routes(app, static_dir_path)
    else:
        logger.warning(
            "Frontend build not found. Bundled static files missing and %s does "
            "not exist. Run 'npm run build' in frontend/ or install the package properly.",
            cfg.FRONTEND_BUILD_DIR,
        )

    return app


app = create_app()
