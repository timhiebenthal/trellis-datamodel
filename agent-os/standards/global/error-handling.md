## Error handling best practices

This project uses FastAPI for backend error handling and standard JavaScript error handling for frontend.

### Backend Error Handling (FastAPI)
- **HTTP Exception**: Use FastAPI's `HTTPException` for API errors with appropriate status codes
- **User-Friendly Messages**: Provide clear, actionable error messages without exposing technical details or security information
- **Validation Errors**: FastAPI automatically returns 422 errors for invalid Pydantic model validation
- **Specific Exception Types**: Create custom exception classes for domain-specific errors when needed
- **Error Responses**: Return consistent error response format (JSON with error message and status code)
- **File Operations**: Handle file I/O errors gracefully (missing files, permission errors, YAML parsing errors)
- **dbt Artifact Errors**: Handle missing or malformed manifest.json/catalog.json files with clear error messages

### Frontend Error Handling (SvelteKit)
- **Try-Catch Blocks**: Use try-catch blocks for async operations and API calls
- **Error Boundaries**: Handle errors at component level; consider error boundaries for critical sections
- **User Feedback**: Display user-friendly error messages in the UI (not technical stack traces)
- **API Error Handling**: Handle HTTP error responses from FastAPI backend appropriately

### Resource Management
- **File Handles**: Use context managers (`with` statements) for file operations in Python
- **Clean Up**: Always clean up resources (file handles, connections) in finally blocks or context managers
- **YAML Operations**: Handle YAML parsing errors gracefully; validate structure before processing

### Graceful Degradation
- **Missing Artifacts**: Handle missing dbt artifacts gracefully; show helpful messages instead of crashing
- **Invalid Config**: Validate configuration early and provide clear error messages for invalid `trellis.yml`
- **Partial Failures**: Design systems to handle partial failures (e.g., some models fail to load) without breaking entire UI
