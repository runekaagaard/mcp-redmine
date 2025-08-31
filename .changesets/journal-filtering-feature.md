---
"mcp-redmine": minor
---

Add intelligent journal filtering for code review workflows

- Add journal filtering system to identify and extract code review-related entries from Redmine issues
- Implement sophisticated Gerrit pattern matching with multi-layered detection (primary/secondary patterns, URL matching, commit SHA detection)
- Add textile markup parsing for Gerrit-specific formatting with ReDoS vulnerability protection
- Integrate journal filtering with existing response filtering system via `mcp_filter` parameter
- Add `code_review_only` boolean flag to enable aggressive filtering that strips administrative noise
- Fix ReDoS vulnerability in textile parsing regex pattern to prevent denial of service attacks
- Add comprehensive test suite with 101 tests achieving 89-90% coverage on core filtering modules
- Add security tests to prevent future ReDoS vulnerabilities and validate performance with malicious input
- Add integration tests for real API calls and combined filtering scenarios
- Maintain 100% backward compatibility with graceful error handling and fallback to original responses
- Add MCP capabilities documentation for journal filtering options and usage examples
- Add AGENTS.md development guidelines for AI agents working with the codebase
- Update README.md with journal filtering examples and `mcp_filtered` flag documentation
- Remove obsolete test_filtering.py file superseded by comprehensive test suite