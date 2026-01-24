"""API route modules."""
from .manifest import router as manifest_router
from .config import config_router
from .data_model import router as data_model_router
from .schema import router as schema_router
from .exposures import router as exposures_router
from .lineage import router as lineage_router
from .bus_matrix import router as bus_matrix_router
from .business_events import router as business_events_router

__all__ = [
    "manifest_router",
    "config_router",
    "data_model_router",
    "schema_router",
    "exposures_router",
    "lineage_router",
    "bus_matrix_router",
    "business_events_router",
]

