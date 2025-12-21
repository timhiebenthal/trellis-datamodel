## Test coverage best practices

This project uses pytest for backend testing and Vitest/Playwright for frontend testing.

### General Testing Principles
- **Write Minimal Tests During Development**: Do NOT write tests for every change or intermediate step. Focus on completing the feature implementation first, then add strategic tests only at logical completion points
- **Test Only Core User Flows**: Write tests exclusively for critical paths and primary user workflows. Skip writing tests for non-critical utilities and secondary workflows until if/when you're instructed to do so.
- **Defer Edge Case Testing**: Do NOT test edge cases, error states, or validation logic unless they are business-critical. These can be addressed in dedicated testing phases, not during feature development.
- **Test Behavior, Not Implementation**: Focus tests on what the code does, not how it does it, to reduce brittleness
- **Clear Test Names**: Use descriptive names that explain what's being tested and the expected outcome

### Backend Testing (pytest)
- **Test Location**: Place tests in `trellis_datamodel/tests/` directory
- **Test Structure**: Use pytest fixtures (defined in `conftest.py`) for common setup/teardown
- **API Testing**: Use `httpx` for async HTTP client testing of FastAPI endpoints
- **Mocking**: Mock external dependencies (file system, dbt artifacts) to isolate units
- **Fast Execution**: Keep unit tests fast (milliseconds) so developers run them frequently
- **Running Tests**: Use `uv run pytest` to run backend tests

### Frontend Testing
- **Unit Tests (Vitest)**: 
  - Use Vitest for component and utility function testing
  - Place tests alongside source files or in `frontend/tests/` directory
  - Use Testing Library for Svelte component testing
  - Run with `npm run test:unit`
  
- **E2E Tests (Playwright)**:
  - Use Playwright for end-to-end user flow testing
  - Place E2E tests in `frontend/tests/` directory (e.g., `*.spec.ts`)
  - Tests automatically start backend with test data via `globalSetup`
  - Use test data file (`frontend/tests/test_data_model.yml`) to avoid polluting production data
  - Run with `npm run test:e2e` or `make test-e2e`
  
- **Smoke Tests**: Quick runtime checks to catch 500 errors and app crashes (`npm run test:smoke`)

### Test Data Isolation
- **E2E Test Data**: E2E tests use separate test data file and automatically clean up before/after runs
- **Backend Test Data**: Use pytest fixtures to provide test data; avoid modifying production files
