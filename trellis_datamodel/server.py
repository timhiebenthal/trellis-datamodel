"""
Trellis Data - FastAPI Server

This is the FastAPI application that serves the API and frontend.
"""

import os
from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError,
    ConfigurationError,
    FileOperationError,
    FeatureDisabledError,
)
from trellis_datamodel.routes import (
    bus_matrix_router,
    business_events_router,
    config_router,
    data_model_router,
    exposures_router,
    lineage_router,
    manifest_router,
    schema_router,
)


def _configure_cors(app: FastAPI) -> None:
    """Allow all origins for local development."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
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
    app.include_router(exposures_router)
    app.include_router(lineage_router)
    app.include_router(bus_matrix_router)
    app.include_router(business_events_router)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Trellis Data", version="0.1.0")

    _configure_cors(app)
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

    print(f"Serving frontend from: {static_dir_path}")

    _register_routers(app)

    # Mount static files AFTER API routes
    # Important: app.mount() creates a sub-application, so we mount AFTER registering API routes
    # However, mounted apps at "/" will intercept everything, so we need a different approach
    if static_dir_path:
        _mount_static_routes(app, static_dir_path)
    else:
        print(
            f"Warning: Frontend build not found. "
            f"Bundled static files missing and {cfg.FRONTEND_BUILD_DIR} does not exist. "
            f"Run 'npm run build' in frontend/ or install the package properly."
        )

    return app


app = create_app()
