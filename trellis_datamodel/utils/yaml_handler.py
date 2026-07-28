"""
YAML Handler for round-trip editing of DBT schema files.
Preserves comments, formatting, and structure while allowing updates.
"""

import os
from typing import Dict, List, Optional, Any
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq


class YamlHandler:
    """Handler for reading and writing DBT schema YAML files with round-trip capabilities."""

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self.yaml.width = 4096  # Prevent unwanted line wrapping
        # Indent sequences 2 spaces under their parent mapping keys (offset=2)
        # sequence=4 is the total indentation for nested sequence items
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        # Disallow indentless sequences so list items are indented under their parent keys
        self.yaml.indentless_sequences = False

    def load_file(self, file_path: str) -> Optional[Dict]:
        """
        Load a YAML file with round-trip capabilities.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed YAML content or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r") as f:
                return self.yaml.load(f)
        except Exception as e:
            print(f"Error loading YAML file {file_path}: {e}")
            return None

    def save_file(self, file_path: str, data: Dict) -> None:
        """
        Save YAML data to a file with round-trip preservation.

        Args:
            file_path: Path to the YAML file
            data: YAML data to save
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write atomically using a temp file
        temp_path = f"{file_path}.tmp"
        try:
            with open(temp_path, "w") as f:
                self.yaml.dump(data, f)
            os.replace(temp_path, file_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def find_model(self, data: Dict, model_name: str) -> Optional[CommentedMap]:
        """
        Find a specific model entry in the YAML data.

        Args:
            data: Parsed YAML data
            model_name: Name of the model to find

        Returns:
            Model entry or None if not found
        """
        if not data or "models" not in data:
            return None

        models = data.get("models", [])
        for model in models:
            if model.get("name") == model_name:
                return model

        return None

    def ensure_model(self, data: Dict, model_name: str) -> CommentedMap:
        """
        Ensure a model entry exists in the YAML data, creating it if necessary.
        Preserve existing tags if present.

        Args:
            data: Parsed YAML data
            model_name: Name of the model

        Returns:
            Model entry (existing or newly created)
        """
        if "version" not in data:
            data["version"] = 2

        if "models" not in data:
            data["models"] = CommentedSeq()
        elif not isinstance(data["models"], CommentedSeq):
            # Normalize plain Python lists to CommentedSeq for consistent formatting
            data["models"] = CommentedSeq(data["models"])

        model = self.find_model(data, model_name)
        if not model:
            model = CommentedMap()
            model["name"] = model_name
            data["models"].append(model)
        # Don't auto-create tags - let update_model_tags handle it when needed
        return model

    def set_latest_version(self, model: CommentedMap, version: int) -> None:
        """Set or bump latest_version for a versioned model."""
        existing = model.get("latest_version")
        if existing is None or (isinstance(existing, int) and version > existing):
            model["latest_version"] = version

    def ensure_model_version(self, model: CommentedMap, version: int) -> CommentedMap:
        """
        Ensure a version entry exists within a versioned model.

        Args:
            model: Model entry
            version: Version number (e.g., 2)

        Returns:
            Version entry (existing or newly created)
        """
        if "versions" not in model or model.get("versions") is None:
            model["versions"] = CommentedSeq()

        for ver in model["versions"]:
            if ver.get("v") == version:
                return ver

        ver_entry = CommentedMap()
        ver_entry["v"] = version
        model["versions"].append(ver_entry)
        return ver_entry

    def update_model_description(
        self, model: CommentedMap, description: Optional[str]
    ) -> None:
        """
        Update the description of a model.

        Args:
            model: Model entry
            description: New description (or None to skip)
        """
        if description:
            model["description"] = description

    def get_model_tags(self, model: CommentedMap) -> List[str]:
        """Return the list of tags for a model, combining top-level and config tags."""
        top_level_tags = list(model.get("tags", []))
        config = model.get("config", {})
        config_tags = list(config.get("tags", [])) if config else []
        # Combine and deduplicate, preserving order
        seen = set()
        combined = []
        for tag in top_level_tags + config_tags:
            if tag not in seen:
                seen.add(tag)
                combined.append(tag)
        return combined

    def _find_config_insert_position(self, model: CommentedMap) -> Optional[int]:
        """
        Find the best position to insert a config block in a model.
        Places it after description but before columns/versions.

        Returns:
            Index position for insertion, or None to append at end
        """
        keys = list(model.keys())

        # Preferred order: name, description, config, columns/versions/...
        # Insert after description if it exists
        if "description" in keys:
            return keys.index("description") + 1

        # Otherwise insert after name if it exists
        if "name" in keys:
            return keys.index("name") + 1

        # If we have columns or versions, insert before them
        for key in ["columns", "versions", "latest_version"]:
            if key in keys:
                return keys.index(key)

        # Default: append at end (return None)
        return None

    def update_version_tags(self, version: CommentedMap, tags: List[str]) -> None:
        """
        Replace the tags list for a model version using config.tags (dbt convention).
        Skips writing empty tags arrays.
        """
        config = version.get("config")

        # If tags is empty, remove existing tags and don't create new ones
        if not tags:
            if config is not None and "tags" in config:
                del config["tags"]
            return

        # Create config block if needed, placing it after description but before columns
        if config is None:
            config = CommentedMap()
            # Find the best insertion position
            insert_pos = self._find_config_insert_position(version)
            if insert_pos is not None:
                version.insert(insert_pos, "config", config)
            else:
                version["config"] = config
            config = version["config"]

        config["tags"] = tags

    def update_model_tags(self, model: CommentedMap, tags: List[str]) -> None:
        """Replace the tags list for a model, preserving the original location.

        Priority: 1) existing config.tags, 2) existing top-level tags, 3) config.tags (default)
        Ensures tags are only in one location to avoid confusion.
        Skips writing empty tags arrays.
        """
        config = model.get("config")
        has_config_tags = config is not None and "tags" in config
        has_top_level_tags = "tags" in model

        # If tags is empty, remove existing tags and don't create new ones
        if not tags:
            if has_config_tags:
                del config["tags"]
            if has_top_level_tags:
                del model["tags"]
            return

        if has_config_tags:
            # Update in config block (original location)
            config["tags"] = tags
            # Remove top-level tags if present to avoid duplication
            if has_top_level_tags:
                del model["tags"]
        elif has_top_level_tags:
            # Update existing top-level tags
            model["tags"] = tags
        else:
            # Default: use config.tags (dbt convention)
            if config is None:
                config = CommentedMap()
                # Find the best insertion position
                insert_pos = self._find_config_insert_position(model)
                if insert_pos is not None:
                    model.insert(insert_pos, "config", config)
                else:
                    model["config"] = config
                config = model["config"]
            config["tags"] = tags

    def merge_model_tags(
        self,
        model: CommentedMap,
        trellis_tags: Optional[List[str]],
        previously_pushed: Optional[List[str]] = None,
    ) -> None:
        """Additively union `trellis_tags` into a model's existing tags, dropping only
        tags in `previously_pushed` that are no longer present in `trellis_tags`.

        No-op when `trellis_tags is None` (Trellis has no opinion on tags this push).
        Tags outside `previously_pushed` (e.g. added directly in schema.yml by dbt) are
        never touched, since dbt owns tags it did not receive from Trellis.
        """
        if trellis_tags is None:
            return

        current_tags = self.get_model_tags(model)
        dropped = set(previously_pushed or []) - set(trellis_tags)
        merged = [tag for tag in current_tags if tag not in dropped]

        seen = set(merged)
        for tag in trellis_tags:
            if tag not in seen:
                seen.add(tag)
                merged.append(tag)

        self.update_model_tags(model, merged)

    def merge_version_tags(
        self,
        version: CommentedMap,
        trellis_tags: Optional[List[str]],
        previously_pushed: Optional[List[str]] = None,
    ) -> None:
        """Additively union `trellis_tags` into a version's existing tags, dropping only
        tags in `previously_pushed` that are no longer present in `trellis_tags`.

        No-op when `trellis_tags is None` (Trellis has no opinion on tags this push).
        Tags outside `previously_pushed` (e.g. added directly in schema.yml by dbt) are
        never touched, since dbt owns tags it did not receive from Trellis.
        """
        if trellis_tags is None:
            return

        current_tags = list(version.get("config", {}).get("tags", []))
        dropped = set(previously_pushed or []) - set(trellis_tags)
        merged = [tag for tag in current_tags if tag not in dropped]

        seen = set(merged)
        for tag in trellis_tags:
            if tag not in seen:
                seen.add(tag)
                merged.append(tag)

        self.update_version_tags(version, merged)

    def find_column(
        self, model: CommentedMap, column_name: str
    ) -> Optional[CommentedMap]:
        """
        Find a specific column entry in the model.

        Args:
            model: Model entry
            column_name: Name of the column to find

        Returns:
            Column entry or None if not found
        """
        columns = model.get("columns", [])
        for col in columns:
            if col.get("name") == column_name:
                return col
        return None

    def ensure_column(self, model: CommentedMap, column_name: str) -> CommentedMap:
        """
        Ensure a column entry exists in the model, creating it if necessary.

        Args:
            model: Model entry
            column_name: Name of the column

        Returns:
            Column entry (existing or newly created)
        """
        if "columns" not in model:
            model["columns"] = CommentedSeq()

        col = self.find_column(model, column_name)
        if not col:
            col = CommentedMap()
            col["name"] = column_name
            model["columns"].append(col)

        return col

    def update_column(
        self,
        column: CommentedMap,
        data_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Update column properties.

        Args:
            column: Column entry
            data_type: New data type (or None to skip)
            description: New description (or None to skip)
        """
        if data_type:
            column["data_type"] = data_type
        if description:
            column["description"] = description

    def remove_relationship_test(
        self,
        column: CommentedMap,
    ) -> None:
        """
        Remove any relationship test from a column, keeping other tests.

        Args:
            column: Column entry
        """
        existing_tests = CommentedSeq()

        # Collect non-relationship tests only
        for key in ("data_tests", "tests"):
            if key not in column:
                continue
            for test in column.get(key, []):
                if isinstance(test, dict) and "relationships" in test:
                    # Skip relationship tests - we're removing them
                    continue
                existing_tests.append(test)

        # Update column with non-relationship tests only
        if len(existing_tests) > 0:
            column["data_tests"] = existing_tests
        else:
            # Remove data_tests key if no tests remain
            if "data_tests" in column:
                del column["data_tests"]
        
        # Drop tests key if present to avoid confusion
        if "tests" in column:
            del column["tests"]

    def add_relationship_test(
        self,
        column: CommentedMap,
        target_model: str,
        target_field: str,
    ) -> None:
        """
        Add or update a relationship test for a column.

        Args:
            column: Column entry
            target_model: Target model name (will be wrapped in ref())
            target_field: Target field name
        """
        existing_tests = CommentedSeq()
        existing_relationship: Optional[CommentedMap] = None

        # Collect non-relationship tests and capture existing relationship test (to preserve tags)
        for key in ("data_tests", "tests"):
            if key not in column:
                continue
            for test in column.get(key, []):
                if isinstance(test, dict) and "relationships" in test:
                    # Keep the first relationships test we find so we can preserve its metadata (e.g., tags)
                    if existing_relationship is None:
                        existing_relationship = test
                    continue
                existing_tests.append(test)

        # Build (or update) relationships test using the recommended arguments block
        rel_test = CommentedMap()
        rel_body = CommentedMap()

        # Preserve existing tags (or any other metadata except arguments, to, and field) on the relationships block
        # Skip "to" and "field" as they are old-style syntax that should be replaced by the new "arguments" block
        if existing_relationship and isinstance(
            existing_relationship.get("relationships"), dict
        ):
            for key, value in existing_relationship["relationships"].items():
                if key in ("arguments", "to", "field"):
                    continue  # arguments/to/field will be rebuilt with the new ref/field syntax
                rel_body[key] = value

        # Always set arguments with the latest reference targets
        rel_body["arguments"] = CommentedMap()
        rel_body["arguments"]["to"] = f"ref('{target_model}')"
        rel_body["arguments"]["field"] = target_field

        rel_test["relationships"] = rel_body
        existing_tests.append(rel_test)

        column["data_tests"] = existing_tests
        # Drop tests key if present to avoid confusion
        if "tests" in column:
            del column["tests"]

    def update_columns_batch(
        self,
        model: CommentedMap,
        columns_data: List[Dict[str, Any]],
    ) -> None:
        """
        Replace the column list of a model with ``columns_data``.

        Existing column entries are reused (preserving tests, meta, and any
        other round-tripped keys) when their ``name`` appears in
        ``columns_data``. Columns missing from the incoming list are dropped,
        so renames/deletions in the data model propagate to schema.yml.
        Final order follows ``columns_data``.

        ``data_type`` is applied as a hard override; ``data_type_fallback``
        only fills in a column that doesn't already declare a data_type
        (used for dbt-sourced fields, where dbt/the warehouse — not
        Trellis — owns the declared type once it exists, see #111).
        """
        existing_by_name: Dict[str, CommentedMap] = {}
        for col in model.get("columns", []) or []:
            name = col.get("name") if isinstance(col, dict) else None
            if name:
                existing_by_name[name] = col

        new_columns = CommentedSeq()
        for col_data in columns_data:
            col_name = col_data.get("name")
            if not col_name:
                continue

            col = existing_by_name.get(col_name)
            if col is None:
                col = CommentedMap()
                col["name"] = col_name

            self.update_column(
                col,
                data_type=self._resolve_data_type(col, col_data),
                description=col_data.get("description"),
            )
            if "meta" in col_data:
                col["meta"] = col_data["meta"]
            new_columns.append(col)

        model["columns"] = new_columns

    @staticmethod
    def _resolve_data_type(
        col: CommentedMap, col_data: Dict[str, Any]
    ) -> Optional[str]:
        """Decide the data_type to write for a column update.

        ``data_type`` always wins when present. Otherwise ``data_type_fallback``
        is applied only if the column doesn't already declare one.
        """
        if "data_type" in col_data:
            return col_data.get("data_type")
        if not col.get("data_type"):
            return col_data.get("data_type_fallback")
        return None

    def merge_columns_non_destructive(
        self,
        model: CommentedMap,
        columns_data: List[Dict[str, Any]],
    ) -> None:
        """
        Merge ``columns_data`` into the model's existing column list without
        deleting columns that are absent from the incoming list.

        - Incoming columns that already exist: updated (data_type, description).
        - Incoming columns that are new: appended.
        - Existing columns not in the incoming list: preserved unchanged.

        Order: incoming columns first (in incoming order), then surviving
        existing columns not present in the incoming list.
        """
        existing_by_name: Dict[str, CommentedMap] = {}
        existing_order: List[str] = []
        for col in model.get("columns", []) or []:
            name = col.get("name") if isinstance(col, dict) else None
            if name:
                existing_by_name[name] = col
                existing_order.append(name)

        incoming_names: List[str] = []
        new_columns = CommentedSeq()

        for col_data in columns_data:
            col_name = col_data.get("name")
            if not col_name:
                continue
            incoming_names.append(col_name)
            col = existing_by_name.get(col_name)
            if col is None:
                col = CommentedMap()
                col["name"] = col_name
            self.update_column(
                col,
                data_type=self._resolve_data_type(col, col_data),
                description=col_data.get("description"),
            )
            if "meta" in col_data:
                col["meta"] = col_data["meta"]
            new_columns.append(col)

        incoming_set = set(incoming_names)
        for name in existing_order:
            if name not in incoming_set:
                new_columns.append(existing_by_name[name])

        model["columns"] = new_columns

    _ORIGIN_SEPARATOR = " | Origin: "
    _ORIGIN_PREFIX = "Origin: "

    @staticmethod
    def _parse_description_with_origin(
        raw_description: str | None,
    ) -> tuple[str | None, str | None]:
        """Split a schema.yml description into (description, origin).

        The write paths embed origin into the description as:
          - "desc | Origin: value"  (both present)
          - "Origin: value"         (only origin, no description)

        This method reverses that encoding so the origin round-trips
        through a dedicated field instead of staying glued to the
        description.
        """
        if not raw_description:
            return raw_description, None

        sep_idx = raw_description.find(YamlHandler._ORIGIN_SEPARATOR)
        if sep_idx != -1:
            desc = raw_description[:sep_idx]
            origin = raw_description[sep_idx + len(YamlHandler._ORIGIN_SEPARATOR) :]
            return (desc or None), (origin or None)

        if raw_description.startswith(YamlHandler._ORIGIN_PREFIX):
            origin = raw_description[len(YamlHandler._ORIGIN_PREFIX) :]
            return None, (origin or None)

        return raw_description, None

    def get_columns(self, model: CommentedMap) -> List[Dict[str, Any]]:
        """
        Extract columns from a model as a list of dicts.

        Args:
            model: Model entry

        Returns:
            List of column dicts
        """
        columns = model.get("columns", [])
        result = []

        for col in columns:
            raw_description = col.get("description")
            description, origin = self._parse_description_with_origin(raw_description)

            col_dict = {
                "name": col.get("name"),
                "data_type": col.get("data_type"),
                "description": description,
            }
            if origin is not None:
                col_dict["origin"] = origin

            # Extract tests (supports both dbt's tests and data_tests keys)
            collected_tests: list[dict[str, Any]] = []
            for key in ("data_tests", "tests"):
                if key not in col:
                    continue
                for test in col.get(key, []):
                    if isinstance(test, dict):
                        collected_tests.append(dict(test))

            if collected_tests:
                col_dict["data_tests"] = collected_tests

            result.append(col_dict)

        return result
