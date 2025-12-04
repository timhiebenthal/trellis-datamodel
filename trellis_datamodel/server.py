"""
Trellis Data - FastAPI Server

This is the FastAPI application that serves the API and frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

    # Include routers
    app.include_router(manifest_router)
    app.include_router(data_model_router)
    app.include_router(schema_router)

    # Mount static files (Frontend) - must be after API routes
    # Try bundled static files first (from package), then fallback to local build
    try:
        # Try to get static files from package
        static_dir = files("trellis_datamodel") / "static"
        if static_dir.is_dir() and any(static_dir.iterdir()):
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        elif os.path.exists(FRONTEND_BUILD_DIR):
            # Fallback to local build directory (for development)
            app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
        else:
            print(
                f"Warning: Frontend build not found. "
                f"Bundled static files missing and {FRONTEND_BUILD_DIR} does not exist. "
                f"Run 'npm run build' in frontend/ or install the package properly."
            )
    except Exception as e:
        # If importlib.resources fails, try local build
        if os.path.exists(FRONTEND_BUILD_DIR):
            app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
        else:
            print(f"Warning: Could not load static files: {e}")

    return app


app = create_app()

