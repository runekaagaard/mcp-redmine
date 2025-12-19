import os, yaml, pathlib
from urllib.parse import urljoin

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

### Constants ###

VERSION = "2025.12.19.144900"

# Load OpenAPI spec
current_dir = pathlib.Path(__file__).parent
with open(current_dir / 'redmine_openapi.yml') as f:
    SPEC = yaml.safe_load(f)

# Constants from environment
REDMINE_URL = os.environ['REDMINE_URL']
REDMINE_API_KEY = os.environ['REDMINE_API_KEY']
CONTAINER_ASSETS_MAPPING = os.getenv('CONTAINER_ASSETS_MAPPING')

def _detect_docker_env() -> bool:
    """Check if the server is running inside a Docker container."""
    return os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and any('docker' in line for line in open('/proc/self/cgroup')))

# Determine execution environment once
IS_RUNNING_IN_DOCKER = _detect_docker_env()

# Pre-process path mapping configuration
HOST_PATH_PREFIX = None
CONTAINER_PATH_PREFIX = None

if CONTAINER_ASSETS_MAPPING:
    try:
        _host, _container = CONTAINER_ASSETS_MAPPING.split(':')
        
        # Normalize paths for comparison (remove leading ./, replace \ with /)
        def _normalize(p):
            p = p.replace('\\', '/')
            # Remove all leading dots and slashes to get a clean relative path
            return p.lstrip('./')

        HOST_PATH_PREFIX = _normalize(_host)
        CONTAINER_PATH_PREFIX = _normalize(_container)
    except ValueError:
        get_logger(__name__).warning(f"Invalid CONTAINER_ASSETS_MAPPING format: '{CONTAINER_ASSETS_MAPPING}'. Expected 'host_path:container_path'.")
    except Exception as e:
        get_logger(__name__).warning(f"Error parsing CONTAINER_ASSETS_MAPPING: {e}")

if "REDMINE_REQUEST_INSTRUCTIONS" in os.environ:
    with open(os.environ["REDMINE_REQUEST_INSTRUCTIONS"]) as f:
        REDMINE_REQUEST_INSTRUCTIONS = f.read()
else:
    REDMINE_REQUEST_INSTRUCTIONS = ""


# Core
def request(path: str, method: str = 'get', data: dict = None, params: dict = None,
            content_type: str = 'application/json', content: bytes = None) -> dict:
    headers = {'X-Redmine-API-Key': REDMINE_API_KEY, 'Content-Type': content_type}
    url = urljoin(REDMINE_URL, path.lstrip('/'))

    try:
        response = httpx.request(method=method.lower(), url=url, json=data, params=params, headers=headers,
                                 content=content, timeout=60.0)
        response.raise_for_status()

        body = None
        if response.content:
            try:
                body = response.json()
            except ValueError:
                body = response.content

        return {"status_code": response.status_code, "body": body, "error": ""}
    except Exception as e:
        try:
            status_code = e.response.status_code
        except:
            status_code = 0

        try:
            body = e.response.json()
        except:
            try:
                body = e.response.text
            except:
                body = None

        return {"status_code": status_code, "body": body, "error": f"{e.__class__.__name__}: {e}"}
        
def yd(obj):
    # Allow direct Unicode output, prevent line wrapping for long lines, and avoid automatic key sorting.
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=4096)


def yd(obj):
    # Allow direct Unicode output, prevent line wrapping for long lines, and avoid automatic key sorting.
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=4096)

def map_host_to_container(file_path: str) -> str:
    """
    Map a host path (AI view) to a container path using pre-parsed prefixes.
    """
    if not HOST_PATH_PREFIX or not CONTAINER_PATH_PREFIX:
        # get_logger(__name__).debug(f"Mapping disabled: prefixes not set")
        return file_path

    try:
        # Normalize input path for comparison
        norm_input = file_path.replace('\\', '/')
        if norm_input.startswith('./'): norm_input = norm_input[2:]
        norm_input = norm_input.rstrip('/')

        # Check if the input path starts with the host prefix
        if norm_input.startswith(HOST_PATH_PREFIX):
            # Extract relative part
            rel_part = norm_input[len(HOST_PATH_PREFIX):].lstrip('/')
            
            # Construct new path using pathlib for safety
            new_path = pathlib.Path(CONTAINER_PATH_PREFIX) / rel_part
            
            get_logger(__name__).info(f"Mapping success: '{file_path}' (norm: '{norm_input}') -> '{new_path}'")
            return str(new_path)
        else:
            get_logger(__name__).info(f"Mapping skip: '{norm_input}' does not start with '{HOST_PATH_PREFIX}'")
            
    except Exception as e:
        get_logger(__name__).error(f"Path mapping failed: {e}")
    
    return file_path

def find_file_in_docker(filename: str) -> pathlib.Path | None:
    """
    Recursively search for a file by name in the assets directory.
    Only intended for use within a Docker container to resolve path mapping issues.
    Search root is determined by CONTAINER_ASSETS_MAPPING (defaulting to 'assets').
    """
    try:
        # Determine search root: prefer mapping config, fallback to default 'assets'
        target_dir = CONTAINER_PATH_PREFIX if CONTAINER_PATH_PREFIX else 'assets'
        search_root = pathlib.Path.cwd() / target_dir
        
        if not search_root.exists() or not search_root.is_dir():
            return None

        # Using rglob to find the first match
        match = next(search_root.rglob(filename), None)
        return match
    except Exception:
        return None


# Tools
mcp = FastMCP("Redmine MCP server")
get_logger(__name__).info(f"Starting MCP Redmine version {VERSION}")
# Mandatory startup log for debugging environment
get_logger(__name__).info(f"Environment: Docker={IS_RUNNING_IN_DOCKER}, MappingConfig='{CONTAINER_ASSETS_MAPPING}', HostPrefix='{HOST_PATH_PREFIX}', ContainerPrefix='{CONTAINER_PATH_PREFIX}'")

@mcp.tool(description="""
Make a request to the Redmine API

Args:
    path: API endpoint path (e.g. '/issues.json')
    method: HTTP method to use (default: 'get')
    data: Dictionary for request body (for POST/PUT)
    params: Dictionary for query parameters

Returns:
    str: YAML string containing response status code, body and error message

{} """.format(REDMINE_REQUEST_INSTRUCTIONS).strip())

def redmine_request(path: str, method: str = 'get', data: dict = None, params: dict = None) -> str:
    return yd(request(path, method=method, data=data, params=params))

@mcp.tool()
def redmine_paths_list() -> str:
    """Return a list of available API paths from OpenAPI spec
    
    Retrieves all endpoint paths defined in the Redmine OpenAPI specification. Remember that you can use the
    redmine_paths_info tool to get the full specfication for a path. 
    
    Returns:
        str: YAML string containing a list of path templates (e.g. '/issues.json')
    """
    return yd(list(SPEC['paths'].keys()))

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

    return yd(info)

@mcp.tool()
def redmine_upload(file_path: str, description: str = None) -> str:
    """
    Upload a file to Redmine and get a token for attachment
    
    Args:
        file_path: Path to the file to upload.
                  Note: In Docker/Container environments, relative paths (e.g., 'assets/image.png') are preferred to avoid cross-platform issues.
                  In native execution, absolute paths are required for security.
        description: Optional description for the file
        
    Returns:
        str: YAML string containing response status code, body and error message
             The body contains the attachment token
    """
    try:
        # Apply container path mapping if configured and running in Docker
        if IS_RUNNING_IN_DOCKER:
            file_path = map_host_to_container(file_path)

        path = pathlib.Path(file_path).expanduser()
        
        # Enforce absolute path only if NOT running in Docker
        if not IS_RUNNING_IN_DOCKER:
            assert path.is_absolute(), f"Path must be fully qualified, got: {file_path}"
        
        if not path.exists():
            # Rescue attempt for Docker environments: Search for the file by name
            if IS_RUNNING_IN_DOCKER:
                found_path = find_file_in_docker(path.name)
                if found_path:
                    path = found_path
                else:
                    return yd({"status_code": 0, "body": None, "error": f"File does not exist: {file_path} (and could not be found via search in {pathlib.Path.cwd()})"})
            else:
                return yd({"status_code": 0, "body": None, "error": f"File does not exist: {file_path}"})

        params = {'filename': path.name}
        if description:
            params['description'] = description

        with open(path, 'rb') as f:
            file_content = f.read()

        result = request(path='uploads.json', method='post', params=params,
                         content_type='application/octet-stream', content=file_content)
        return yd(result)
    except Exception as e:
        return yd({"status_code": 0, "body": None, "error": f"{e.__class__.__name__}: {e}"})

@mcp.tool()
def redmine_download(attachment_id: int, save_path: str, filename: str = None) -> str:
    """
    Download an attachment from Redmine and save it to a local file
    
    Args:
        attachment_id: The ID of the attachment to download
        save_path: The path where the file should be saved. 
                  Note: In Docker/Container environments, relative paths (e.g., 'assets/file.txt') are preferred to avoid cross-platform issues.
                  In native execution, absolute paths are required for security.
        filename: Optional filename to use for the attachment. If not provided,
                 will be determined from attachment data or URL

    Returns:
        str: YAML string containing download status, file path, and any error messages
    """
    try:
        # Apply container path mapping if configured and running in Docker
        if IS_RUNNING_IN_DOCKER:
            save_path = map_host_to_container(save_path)

        path = pathlib.Path(save_path).expanduser()
        
        # Enforce absolute path and restrict directory usage only if NOT running in Docker
        if not IS_RUNNING_IN_DOCKER:
            assert path.is_absolute(), f"Path must be fully qualified, got: {save_path}"
            assert not path.is_dir(), f"Path can't be a directory, got: {save_path}"

        if not filename:
            attachment_response = request(f"attachments/{attachment_id}.json", "get")
            if attachment_response["status_code"] != 200:
                return yd(attachment_response)

            filename = attachment_response["body"]["attachment"]["filename"]

        # Ensure directory exists
        if path.is_dir() or save_path.endswith(("/", "\\")):
            path.mkdir(parents=True, exist_ok=True)
            path = path / filename
        else:
            path.parent.mkdir(parents=True, exist_ok=True)

        response = request(f"attachments/download/{attachment_id}/{filename}", "get",
                           content_type="application/octet-stream")
        if response["status_code"] != 200 or not response["body"]:
            return yd(response)

        with open(path, 'wb') as f:
            f.write(response["body"])

        return yd({"status_code": 200, "body": {"saved_to": str(path), "filename": filename}, "error": ""})
    except Exception as e:
        return yd({"status_code": 0, "body": None, "error": f"{e.__class__.__name__}: {e}"})
def main():
    """Main entry point for the mcp-redmine package."""
    mcp.run()

if __name__ == "__main__":
    main()
