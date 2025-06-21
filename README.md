# MCP Redmine

**Status: Works great and is in daily use without any known bugs.**

**Status2: I just added the package to PyPI and updated the usage instructions. Please report any issues :)**

Let Claude be your Redmine assistant! MCP Redmine connects Claude Desktop to your Redmine instance, allowing it to:

- Search and browse projects and issues
- Create and update issues with full markdown support
- Upload and download file attachments
- Manage and track time entries
- Update issue statuses and fields
- Access comprehensive Redmine API functionality

Uses httpx for API requests and integrates with the Redmine OpenAPI specification for comprehensive API coverage.

![MCP Redmine in action](https://raw.githubusercontent.com/runekaagaard/mcp-redmine/refs/heads/main/screenshot.png)

## Installation

Ensure you have uv installed. 
```bash
uv --version
```

Install uv if you haven't already.

- Linux
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- macOS
  ```zsh
  brew install uv
  ```

- windows
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "uvx",
      "args": ["--from", "mcp-redmine==2025.04.09.153531", 
               "--refresh-package", "mcp-redmine", "mcp-redmine"],
      "env": {
        "REDMINE_URL": "https://your-redmine-instance.example.com",
        "REDMINE_API_KEY": "your-api-key",
        "REDMINE_REQUEST_INSTRUCTIONS": "/path/to/instructions.md"
      }
    }
  }
}
```

## Environment Variables

- `REDMINE_URL`: URL of your Redmine instance (required)
- `REDMINE_API_KEY`: Your Redmine API key (required, see below for how to get it)
- `REDMINE_REQUEST_INSTRUCTIONS`: Path to a file containing additional instructions for the redmine_request tool (optional). I've found it works great to have the LLM generate that file after a session. ([example1](INSTRUCTIONS_EXAMPLE1.md) [example2](INSTRUCTIONS_EXAMPLE2.md))

## Getting Your Redmine API Key

1. Log in to your Redmine instance
2. Go to "My account" (typically found in the top-right menu)
3. On the right side of the page, you should see "API access key"
4. Click "Show" to view your existing key or "Generate" to create a new one
5. Copy this key for use in your configuration

## API

### Tools

- **redmine_paths_list**
  - Return a list of available API paths from OpenAPI spec
  - No input required
  - Returns a YAML string containing a list of path templates:
  ```
  - /issues.json
  - /projects.json
  - /time_entries.json
  ...
  ```

- **redmine_paths_info**
  - Get full path information for given path templates
  - Input: `path_templates` (list of strings)
  - Returns YAML string containing API specifications for the requested paths:
  ```yaml
  /issues.json:
    get:
      operationId: getIssues
      parameters:
        - $ref: '#/components/parameters/format'
      ...
  ```

- **redmine_request**
  - Make a request to the Redmine API
  - Inputs:
    - `path` (string): API endpoint path (e.g. '/issues.json')
    - `method` (string, optional): HTTP method to use (default: 'get')
    - `data` (object, optional): Dictionary for request body (for POST/PUT)
    - `params` (object, optional): Dictionary for query parameters
  - Returns YAML string containing response status code, body and error message:
  ```yaml
  status_code: 200
  body:
    issues:
      - id: 1
        subject: "Fix login page"
        ...
  error: ""
  ```

- **redmine_upload**
  - Upload a file to Redmine and get a token for attachment
  - Inputs:
    - `file_path` (string): Fully qualified path to the file to upload
    - `description` (string, optional): Optional description for the file
  - Returns YAML string with the same format as redmine_request, including upload token:
  ```yaml
  status_code: 201
  body:
    upload:
      id: 7
      token: "7.ed32257a2ab0f7526c0d72c32994c58b131bb2c0775f7aa84aae01ea8397ea54"
  error: ""
  ```

- **redmine_download**
  - Download an attachment from Redmine and save it to a local file
  - Inputs:
    - `attachment_id` (integer): The ID of the attachment to download
    - `save_path` (string): Fully qualified path where the file should be saved
    - `filename` (string, optional): Optional filename to use (determined automatically if not provided)
  - Returns YAML string with download results:
  ```yaml
  status_code: 200
  body:
    saved_to: "/path/to/downloaded/file.pdf"
    filename: "file.pdf"
  error: ""
  ```

## Examples

### Creating a new issue

```
Let's create a new bug report in the "Website" project:

1. Title: "Homepage not loading on mobile devices"
2. Description: "When accessing the homepage from iOS or Android devices, the loading spinner appears but the content never loads. This issue started after the last deployment."
3. Priority: High
4. Assign to: John Smith
```

### Searching for issues

```
Can you find all high priority issues in the "Website" project that are currently unassigned?
```

### Updating issue status

```
Please mark issue #123 as "In Progress" and add a comment: "I've started working on this issue. Expect it to be completed by Friday."
```

### Logging time

```
Log 3.5 hours against issue #456 for "Implementing user authentication" done today.
```

## MCP Directory Listings

MCP Redmine is listed in the following MCP directory sites and repositories:

- [MCP.so](https://mcp.so/server/mcp-redmine)
- [Glama](https://glama.ai/mcp/servers/@runekaagaard/mcp-redmine)

## Developing

First clone the github repository and install the dependencies:

```
git clone git@github.com:runekaagaard/mcp-redmine.git
cd mcp-redmine
uv sync
```

Then set this in claude_desktop_config.json:

```
...
"command": "uv",
"args": ["run", "--directory", "/path/to/mcp-redmine", "-m", "mcp_redmine.server", "main"],
...
```

## My Other LLM Projects

- **[MCP Alchemy](https://github.com/runekaagaard/mcp-alchemy)** - Connect Claude Desktop to databases for exploring schema and running SQL.
- **[MCP Notmuch Sendmail](https://github.com/runekaagaard/mcp-notmuch-sendmail)** - Email assistant for Claude Desktop using notmuch.
- **[Diffpilot](https://github.com/runekaagaard/diffpilot)** - Multi-column git diff viewer with file grouping and tagging.
- **[Claude Local Files](https://github.com/runekaagaard/claude-local-files)** - Access local files in Claude Desktop artifacts.

## Contributing

Contributions are warmly welcomed! Whether it's bug reports, feature requests, documentation improvements, or code contributions - all input is valuable. Feel free to:

- Open an issue to report bugs or suggest features
- Submit pull requests with improvements
- Enhance documentation or share your usage examples
- Ask questions and share your experiences

The goal is to make Redmine project management with Claude even better, and your insights and contributions help achieve that.

## Acknowledgments

This project builds on the excellent work of others:

- [httpx](https://www.python-httpx.org/) - For handling HTTP requests
- [Redmine OpenAPI Specification](https://github.com/d-yoshi/redmine-openapi) - For the comprehensive API specification
- [Redmine](https://www.redmine.org/) - The flexible project management web application

## License

Mozilla Public License Version 2.0
