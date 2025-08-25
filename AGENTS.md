# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build/Test Commands
- `make test` - Run tests using uv with dev dependencies (not standard pytest)
- `make test-coverage` - Generate HTML coverage reports in htmlcov/
- `uv sync --group dev` - Install dev dependencies (required before testing)
- `uv run --group dev pytest tests/ -v` - Direct test execution with uv

## Project-Specific Patterns
- **Environment Variables Required**: REDMINE_URL and REDMINE_API_KEY must be set or server fails to start
- **Response Filtering Architecture**: All API responses go through apply_response_filter() with backward compatibility fallback
- **Filter Presets**: Use string preset names ("minimal", "clean", "essential_issues") that get converted to dict configs
- **Error Handling Pattern**: All tools return YAML with {status_code, body, error} structure, never raise exceptions
- **File Path Requirements**: Upload/download tools require fully qualified absolute paths, not relative paths
- **OpenAPI Integration**: redmine_openapi.yml is loaded at startup and used for path validation and MCP capabilities

## Critical Implementation Details
- **Filtering Fallback**: If mcp_filter processing fails, original response is returned (lines 99-102 in server.py)
- **Version Sync**: VERSION constant in server.py must match pyproject.toml version for releases
- **MCP Tool Decoration**: All tools use @mcp.tool() decorator and return YAML strings, not Python objects
- **Custom Fields Handling**: Special filtering logic for custom_fields arrays based on field names
- **Content-Type Switching**: Upload tool switches to 'application/octet-stream' for file uploads

## Testing Requirements
- Tests must use pytest with uv run wrapper
- All filtering tests verify backward compatibility
- Response filter tests check both success and error scenarios
- Preset tests validate all presets work with actual filtering system