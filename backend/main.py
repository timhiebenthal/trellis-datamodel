from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import yaml
import os

app = FastAPI()

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# dbt-ontology/backend/../../dbt/target/manifest.json -> root/dbt/target/manifest.json
MANIFEST_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../dbt/target/manifest.json"))
# dbt-ontology/backend/../ontology.yml -> dbt-ontology/ontology.yml
ONTOLOGY_PATH = os.path.abspath(os.path.join(BASE_DIR, "../ontology.yml"))

print(f"Looking for manifest at: {MANIFEST_PATH}")
print(f"Looking for ontology at: {ONTOLOGY_PATH}")

@app.get("/api/manifest")
async def get_manifest():
    if not os.path.exists(MANIFEST_PATH):
        raise HTTPException(status_code=404, detail=f"Manifest not found at {MANIFEST_PATH}")
    
    try:
        with open(MANIFEST_PATH, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading manifest: {str(e)}")

    models = []
    for key, node in data.get("nodes", {}).items():
        if node.get("resource_type") == "model":
            columns = []
            for col_name, col_data in node.get("columns", {}).items():
                columns.append({
                    "name": col_name,
                    "type": col_data.get("type")
                })
            
            models.append({
                "name": node.get("name"),
                "schema": node.get("schema"),
                "table": node.get("alias", node.get("name")),
                "columns": columns
            })
    
    models.sort(key=lambda x: x["name"])
    return {"models": models}

@app.get("/api/ontology")
async def get_ontology():
    if not os.path.exists(ONTOLOGY_PATH):
        return {"version": 0.1, "entities": [], "relationships": []}
    
    try:
        with open(ONTOLOGY_PATH, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        if not data.get("entities"): data["entities"] = []
        if not data.get("relationships"): data["relationships"] = []
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading ontology: {str(e)}")

class OntologyUpdate(BaseModel):
    version: float = 0.1
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]

@app.post("/api/ontology")
async def save_ontology(data: OntologyUpdate):
    try:
        content = data.model_dump()
        with open(ONTOLOGY_PATH, 'w') as f:
            yaml.dump(content, f, default_flow_style=False, sort_keys=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving ontology: {str(e)}")

# Mount static files (Frontend)
# Must be after API routes
FRONTEND_BUILD_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend/build"))

if os.path.exists(FRONTEND_BUILD_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
else:
    print(f"Warning: Frontend build not found at {FRONTEND_BUILD_DIR}. Run 'npm run build' in frontend/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
