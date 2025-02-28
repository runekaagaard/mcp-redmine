import os, yaml
import pathlib
from urllib.parse import urljoin

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

    url = urljoin(REDMINE_URL, path)

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
def redmine_upload(absolute_file_path: str, description: str = None) -> str:
    """
    Upload a file to Redmine and get a token for attachment
    
    Args:
        absolute_file_path: Absolute path to the file to upload (must be absolute, not relative)
        description: Optional description for the file
        
    Returns:
        str: YAML string containing response status code, body and error message
             The body contains token and filename when successful
    """
    path = pathlib.Path(absolute_file_path)
    if not path.is_absolute():
        return yaml.dump({
            "status_code": 0,
            "body": "",
            "error": f"Path must be absolute, got: {absolute_file_path}"
        })
    if not path.exists():
        return yaml.dump({"status_code": 0, "body": "", "error": f"File does not exist: {absolute_file_path}"})

    filename = path.name
    url = urljoin(REDMINE_URL, 'uploads.json')

    headers = {
        'X-Redmine-API-Key': REDMINE_API_KEY,
        'Content-Type': 'application/octet-stream',
        'Accept': 'application/json',
    }

    params = {'filename': filename}
    if description:
        params['description'] = description

    try:
        with open(path, 'rb') as f:
            file_content = f.read()

        response = httpx.post(url=url, params=params, headers=headers, content=file_content, timeout=60.0)
        result = {"status_code": response.status_code, "body": "", "error": ""}

        if response.content:
            try:
                result["body"] = response.json()
                if response.status_code == 201 and 'upload' in result["body"]:
                    result["body"]["filename"] = filename
            except ValueError:
                result["body"] = response.text

        return yaml.dump(result)
    except Exception as e:
        # Handle any exceptions (file not found, connection issues, etc.)
        return yaml.dump({"status_code": 0, "body": "", "error": str(e)})

@mcp.tool()
def redmine_paths_list() -> str:
    """Return a list of available API paths from OpenAPI spec
    
    Retrieves all endpoint paths defined in the Redmine OpenAPI specification. Remember that you can use the
    redmine_paths_info tool to get the full specfication for a path.
    
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

@mcp.tool()
def redmine_download(attachment_id: int, absolute_save_path: str, filename: str = None) -> str:
    """
    Download an attachment from Redmine and save it to a local file
    
    Args:
        attachment_id: The ID of the attachment to download
        absolute_save_path: Absolute path where the file should be saved (must be absolute, not relative)
        filename: Optional filename to use for the attachment. If not provided, 
                 will be determined from attachment data or URL
        
    Returns:
        str: YAML string containing download status, file path, and any error messages
    """
    save_path = pathlib.Path(absolute_save_path)
    if not save_path.is_absolute():
        return yaml.dump({
            "status_code": 0,
            "body": "",
            "error": f"Save path must be absolute, got: {absolute_save_path}"
        })

    try:
        if not filename:
            attachment_url = urljoin(REDMINE_URL, f"attachments/{attachment_id}.json")
            headers = {
                'X-Redmine-API-Key': REDMINE_API_KEY,
                'Accept': 'application/json',
            }

            response = httpx.get(url=attachment_url, headers=headers, timeout=30.0)

            if response.status_code != 200:
                return yaml.dump({
                    "status_code": response.status_code,
                    "body": "",
                    "error": f"Failed to get attachment details: {response.text}"
                })

            attachment_data = response.json()
            filename = attachment_data.get('attachment', {}).get('filename')

            if not filename:
                return yaml.dump({
                    "status_code": 0,
                    "body": "",
                    "error": "Could not determine filename from attachment"
                })

        download_url = urljoin(REDMINE_URL, f"attachments/download/{attachment_id}/{filename}")
        headers = {
            'X-Redmine-API-Key': REDMINE_API_KEY,
        }

        if save_path.is_dir():
            save_path = save_path / filename

        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Use a regular request instead of streaming to avoid the read() error
        response = httpx.get(download_url, headers=headers, timeout=60.0)
        
        if response.status_code != 200:
            return yaml.dump({
                "status_code": response.status_code,
                "body": "",
                "error": f"Download failed with status {response.status_code}: {response.text}"
            })

        # Get content length from headers
        total_size = int(response.headers.get('content-length', 0))
        
        # Write response content directly to file
        with open(save_path, 'wb') as f:
            f.write(response.content)

        return yaml.dump({
            "status_code": 200,
            "body": {
                "saved_to": str(save_path),
                "filename": filename,
                "size_bytes": total_size or save_path.stat().st_size
            },
            "error": ""
        })

    except Exception as e:
        # Handle any exceptions
        return yaml.dump({"status_code": 0, "body": "", "error": str(e)})

if __name__ == "__main__":
    mcp.run()
