"""
MCP capabilities documentation and API discovery for Redmine MCP server.

This module provides documentation about the enhanced processing capabilities
that the MCP server adds on top of the native Redmine API. It generates
structured capability information for API discovery and LLM guidance.
"""

from typing import Dict, Any
from .filter_presets import get_preset_documentation


def get_mcp_capabilities(path: str) -> Dict[str, Any]:
    """
    Generate MCP capabilities documentation for a given API path.
    
    Args:
        path: API path (e.g., '/issues.json')
        
    Returns:
        Dictionary containing MCP capabilities documentation
    """
    capabilities = {
        "description": "Enhanced processing capabilities provided by the MCP server",
        "response_filtering": {
            "description": "Reduce response size while preserving essential data",
            "parameter": "mcp_filter",
            "usage": "Add 'mcp_filter' parameter to redmine_request() for response processing",
            "options": {
                "remove_empty": {
                    "type": "boolean",
                    "description": "Remove fields with null/empty values",
                    "default": False,
                    "example": True
                },
                "exclude_fields": {
                    "type": "array",
                    "description": "List of field names to exclude from response",
                    "example": ["custom_fields", "journals"]
                },
                "include_fields": {
                    "type": "array", 
                    "description": "Only include these specific fields (overrides exclude_fields)",
                    "example": ["id", "subject", "status", "assigned_to"]
                },
                "max_description_length": {
                    "type": "integer",
                    "description": "Truncate description fields to this length",
                    "example": 200
                },
                "max_array_items": {
                    "type": "integer",
                    "description": "Limit arrays to this many items",
                    "example": 10
                }
            },
            "presets": {
                "description": "Predefined filter configurations for common use cases",
                "usage": "Use preset name as mcp_filter value (e.g., mcp_filter='clean')",
                "available_presets": get_preset_documentation()
            }
        }
    }
    
    # Add path-specific filtering options
    if "issues" in path:
        capabilities["response_filtering"]["options"]["remove_custom_fields"] = {
            "type": "boolean",
            "description": "Remove all custom_fields array",
            "default": False,
            "example": True
        }
        capabilities["response_filtering"]["options"]["keep_custom_fields"] = {
            "type": "array",
            "description": "Keep only these custom fields by name",
            "example": ["Build", "Owner", "Priority"]
        }
    
    return capabilities
