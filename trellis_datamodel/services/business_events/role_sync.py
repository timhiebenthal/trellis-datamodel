"""
Sync roles used in business event annotations onto dimension entities in the
data model.
"""
import logging
from typing import Dict

from trellis_datamodel.models.business_event import BusinessEventAnnotations
from trellis_datamodel.services.data_model import (
    load_data_model_raw,
    save_data_model_raw,
)

logger = logging.getLogger(__name__)


def _sync_roles_to_dimensions(annotations: BusinessEventAnnotations) -> None:
    """
    Sync roles from business event annotations to dimension entities in the data model.
    
    When an annotation has both dimension_id and role set, this ensures the dimension
    entity has that role in its roles array. This keeps the data model in sync with
    how dimensions are being used in business events.
    
    Args:
        annotations: BusinessEventAnnotations object containing dimension references with roles
    """
    try:
        # Collect all dimension_id + role pairs from annotations
        dimension_roles: Dict[str, set] = {}  # dimension_id -> set of roles
        
        for annotation_type in ["who", "what", "when", "where", "how", "why"]:
            category_list = getattr(annotations, annotation_type, [])
            for entry in category_list:
                dim_id = getattr(entry, "dimension_id", None)
                role = getattr(entry, "role", None)
                
                if dim_id and role:
                    if dim_id not in dimension_roles:
                        dimension_roles[dim_id] = set()
                    dimension_roles[dim_id].add(role)
        
        if not dimension_roles:
            return  # No roles to sync
        
        # Load data model
        data_model = load_data_model_raw()
        modified = False
        
        # Update each dimension entity
        entities = data_model.get("entities", [])
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id in dimension_roles:
                # Get current roles (or empty list)
                current_roles = entity.get("roles", [])
                if current_roles is None:
                    current_roles = []
                # Roles are flat strings or structured {label, role, source} objects
                current_roles_set = {
                    (r.get("role") or r.get("label")) if isinstance(r, dict) else r
                    for r in current_roles
                }
                structured = any(isinstance(r, dict) for r in current_roles)
                
                # Add new roles, matching the shape already stored on the entity
                new_roles = dimension_roles[entity_id]
                for role in new_roles:
                    if role not in current_roles_set:
                        current_roles.append(
                            {"label": role, "role": role} if structured else role
                        )
                        modified = True
                
                # Update entity
                entity["roles"] = current_roles
        
        # Save if modified
        if modified:
            save_data_model_raw(data_model)
            logger.info(f"Synced roles to {len(dimension_roles)} dimension(s)")
    
    except Exception as e:
        # Don't fail the annotation save if role sync fails
        logger.warning(f"Failed to sync roles to dimensions: {e}")
