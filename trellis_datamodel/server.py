"""
Trellis Data - FastAPI Server

This is the FastAPI application that serves the API and frontend.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
from importlib.resources import files

from trellis_datamodel import config as cfg
from trellis_datamodel.config import print_config
from trellis_datamodel.routes import manifest_router, data_model_router, schema_router, lineage_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Trellis Data", version="0.1.0")

    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all for local dev
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    # Find static files directory
    # Priority: 1) configured FRONTEND_BUILD_DIR, 2) package static dir (if it has index.html)
    static_dir_path = None

    # Check configured build dir first
    if cfg.FRONTEND_BUILD_DIR and os.path.exists(
        os.path.join(cfg.FRONTEND_BUILD_DIR, "index.html")
    ):
        static_dir_path = cfg.FRONTEND_BUILD_DIR
    else:
        # Fall back to package static dir if it has index.html
        try:
            static_dir = files("trellis_datamodel") / "static"
            if static_dir.is_dir():
                pkg_index = str(static_dir / "index.html")
                if os.path.exists(pkg_index):
                    static_dir_path = str(static_dir)
        except Exception:
            pass

    print(f"Serving frontend from: {static_dir_path}")

    # Include API routers - these MUST be registered before mounting static files
    app.include_router(manifest_router)
    app.include_router(data_model_router)
    app.include_router(schema_router)
    app.include_router(lineage_router)

    # Mount static files AFTER API routes
    # Important: app.mount() creates a sub-application, so we mount AFTER registering API routes
    # However, mounted apps at "/" will intercept everything, so we need a different approach
    if static_dir_path:
        # Serve static assets at /assets
        assets_path = os.path.join(static_dir_path, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        # Serve other static files (like favicon, etc.) at /_app
        # SvelteKit builds put immutable assets in /_app
        app_path = os.path.join(static_dir_path, "_app")
        if os.path.exists(app_path):
            app.mount("/_app", StaticFiles(directory=app_path), name="app")

        # Catch-all route for SPA - must be defined LAST
        # FastAPI matches more specific routes first, so /api/* routes will match before this
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(request: Request, full_path: str):
            """Serve SPA index.html for non-API routes."""
            # Serve index.html for all routes (API routes are already matched above)
            index_file = os.path.join(static_dir_path, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            raise HTTPException(status_code=404, detail="Not found")

    else:
        print(
            f"Warning: Frontend build not found. "
            f"Bundled static files missing and {cfg.FRONTEND_BUILD_DIR} does not exist. "
            f"Run 'npm run build' in frontend/ or install the package properly."
        )

    return app


app = create_app()
