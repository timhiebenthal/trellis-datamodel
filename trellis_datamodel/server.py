"""
Trellis Data - FastAPI Server

This is the FastAPI application that serves the API and frontend.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from importlib.resources import files

from trellis_datamodel.config import FRONTEND_BUILD_DIR, print_config
from trellis_datamodel.routes import manifest_router, data_model_router, schema_router


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

    # Include routers - MUST be before static files
    app.include_router(manifest_router)
    app.include_router(data_model_router)
    app.include_router(schema_router)

    # Find static files directory
    static_dir_path = None
    try:
        # Try to get static files from package
        static_dir = files("trellis_datamodel") / "static"
        if static_dir.is_dir() and any(static_dir.iterdir()):
            static_dir_path = str(static_dir)
    except Exception:
        pass
    
    if not static_dir_path and os.path.exists(FRONTEND_BUILD_DIR):
        static_dir_path = FRONTEND_BUILD_DIR
    
    if static_dir_path:
        # Serve static assets
        assets_path = os.path.join(static_dir_path, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        
        # SPA fallback - serve index.html for non-API routes
        # This must be defined AFTER API routes so they take precedence
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            """Serve the SPA for all non-API routes."""
            index_file = os.path.join(static_dir_path, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            return {"detail": "Not found"}
    else:
        print(
            f"Warning: Frontend build not found. "
            f"Bundled static files missing and {FRONTEND_BUILD_DIR} does not exist. "
            f"Run 'npm run build' in frontend/ or install the package properly."
        )

    return app


app = create_app()

