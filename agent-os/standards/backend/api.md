## API endpoint standards and conventions

This project uses FastAPI for the backend API. Follow these conventions:

- **RESTful Design**: Follow REST principles with clear resource-based URLs and appropriate HTTP methods (GET, POST, PUT, PATCH, DELETE)
- **FastAPI Routers**: Organize endpoints using FastAPI routers in `trellis_datamodel/routes/` directory
- **Consistent Naming**: Use consistent, lowercase, hyphenated naming conventions for endpoints (e.g., `/api/data-model`, `/api/manifest`)
- **Pydantic Models**: Use Pydantic models (defined in `trellis_datamodel/models/schemas.py`) for request/response validation
- **Nested Resources**: Limit nesting depth to 2-3 levels maximum to keep URLs readable and maintainable
- **Query Parameters**: Use query parameters for filtering, sorting, pagination, and search rather than creating separate endpoints
- **HTTP Status Codes**: Return appropriate, consistent HTTP status codes that accurately reflect the response (200, 201, 400, 404, 500, etc.)
- **Static File Serving**: Serve frontend static files from `trellis_datamodel/static/` directory
- **API Documentation**: FastAPI automatically generates OpenAPI docs at `/docs` endpoint
