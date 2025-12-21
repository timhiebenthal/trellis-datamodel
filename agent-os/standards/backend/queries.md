## Query and data access best practices

This project primarily works with dbt artifacts (manifest.json, catalog.json) and YAML files rather than direct database queries.

### dbt Artifact Reading
- **Manifest Parsing**: Read dbt `manifest.json` to understand model structure, dependencies, and metadata
- **Catalog Parsing**: Read dbt `catalog.json` to get column information and types
- **File Path Handling**: Use proper path resolution relative to `dbt_project_path` configuration
- **Error Handling**: Handle missing or malformed JSON files gracefully with clear error messages

### YAML File Operations
- **Preserve Formatting**: Use `ruamel.yaml` (not `pyyaml`) to preserve YAML formatting, comments, and structure when editing
- **Safe Updates**: Read, modify, and write YAML files atomically to avoid corruption
- **Schema Validation**: Validate YAML structure against expected schema before processing
- **Backup Strategy**: Consider backing up YAML files before major modifications

### DuckDB Queries (if needed)
- **Prevent SQL Injection**: Always use parameterized queries; never interpolate user input into SQL strings
- **Select Only Needed Data**: Request only the columns you need rather than using SELECT * for better performance
- **DuckDB-Specific**: Leverage DuckDB's columnar storage and analytical functions when appropriate
- **Connection Management**: Use connection pooling or context managers for database connections
- **Set Query Timeouts**: Implement timeouts to prevent runaway queries from impacting system performance

### Performance Considerations
- **Caching**: Cache parsed manifest/catalog data when appropriate (they don't change frequently)
- **Lazy Loading**: Load dbt artifacts only when needed, not at application startup
- **Incremental Updates**: Consider incremental updates to data model rather than full reloads
