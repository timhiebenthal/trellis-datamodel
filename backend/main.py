"""
Data Model UI - FastAPI Backend

This is the main entry point for the backend API.
Routes are organized into separate modules under the routes/ directory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import FRONTEND_BUILD_DIR, print_config
from routes import manifest_router, data_model_router, schema_router

app = FastAPI(title="Data Model UI", version="0.1.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint for Playwright and monitoring
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Include routers
app.include_router(manifest_router)
app.include_router(data_model_router)
app.include_router(schema_router)

# Print config on startup
print_config()

# Mount static files (Frontend) - must be after API routes
if os.path.exists(FRONTEND_BUILD_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
else:
    print(
        f"Warning: Frontend build not found at {FRONTEND_BUILD_DIR}. Run 'npm run build' in frontend/"
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
