## Validation best practices

This project uses Pydantic for backend validation and TypeScript for frontend type safety.

### Backend Validation (Pydantic)
- **Pydantic Models**: Use Pydantic models (in `trellis_datamodel/models/schemas.py`) for request/response validation
- **FastAPI Integration**: FastAPI automatically validates request bodies against Pydantic models
- **Type Validation**: Leverage Pydantic's built-in type validation (str, int, Optional, List, etc.)
- **Custom Validators**: Use Pydantic validators (`@field_validator`, `@model_validator`) for complex validation logic
- **Fail Early**: FastAPI automatically returns 422 errors for invalid input before reaching route handlers
- **Error Messages**: Pydantic provides detailed error messages; customize with `Field(description=...)` for clarity

### Frontend Validation (TypeScript)
- **Type Safety**: Use TypeScript for compile-time type checking
- **Runtime Validation**: Consider runtime validation libraries if needed for form validation
- **Client-Side UX**: Provide immediate user feedback for invalid input, but always validate server-side

### YAML File Validation
- **Schema Validation**: Validate YAML structure against expected schema before processing
- **dbt Schema Validation**: Validate dbt schema.yml files against dbt's expected structure
- **Data Model Validation**: Validate data_model.yml against project's data model schema

### Security Considerations
- **Path Validation**: Validate file paths to prevent directory traversal attacks
- **YAML Safety**: Use safe YAML loading to prevent code execution vulnerabilities
- **Input Sanitization**: Sanitize user input for file names, entity names, and descriptions
