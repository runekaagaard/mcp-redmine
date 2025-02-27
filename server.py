import os, yaml

import httpx

from mcp.server.fastmcp import FastMCP

# Constants from environment
REDMINE_URL = os.environ['REDMINE_URL']
REDMINE_API_KEY = os.environ['REDMINE_API_KEY']

# Load OpenAPI spec
with open('redmine_openapi.yml') as f:
    SPEC = yaml.safe_load(f)

# Tools

mcp = FastMCP("Redmine MCP server")

@mcp.tool()
def redmine_request(path: str, method: str = 'get', data: dict = None, params: dict = None) -> str:
    """
    Make a request to the Redmine API

    Args:
        path: API endpoint path (e.g. '/issues.json')
        method: HTTP method to use (default: 'get')
        data: Dictionary for request body (for POST/PUT)
        params: Dictionary for query parameters

    Returns:
        str: YAML string containing response status code, body and error message
    """
    headers = {
        'X-Redmine-API-Key': REDMINE_API_KEY,
        'Content-Type': 'application/json',
    }

    url = f"{REDMINE_URL.rstrip('/')}/{path.lstrip('/')}"

    try:
        response = httpx.request(method=method.lower(), url=url, json=data, params=params, headers=headers,
                                 timeout=30.0)

        result = {"status_code": response.status_code, "body": "", "error": ""}

        if response.content:
            try:
                result["body"] = response.json()
            except ValueError:
                result["body"] = response.text

        return yaml.dump(result)

    except Exception as e:
        # Any error (connection errors, timeouts, etc.)
        return yaml.dump({"status_code": 0, "body": "", "error": str(e)})

@mcp.tool()
def redmine_paths_list() -> str:
    """Return a list of available API paths from OpenAPI spec
    
    Retrieves all endpoint paths defined in the Redmine OpenAPI specification.
    
    Returns:
        str: YAML string containing a list of path templates (e.g. '/issues.json')
    """
    return yaml.dump(list(SPEC['paths'].keys()))

@mcp.tool()
def redmine_paths_info(path_templates: list) -> str:
    """Get full path information for given path templates
    
    Args:
        path_templates: List of path templates (e.g. ['/issues.json', '/projects.json'])
        
    Returns:
        str: YAML string containing API specifications for the requested paths
    """
    info = {}
    for path in path_templates:
        if path in SPEC['paths']:
            info[path] = SPEC['paths'][path]

    return yaml.dump(info)

if __name__ == "__main__":
    mcp.run()
