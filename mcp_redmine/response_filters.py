"""
Response filtering and transformation utilities for Redmine MCP server.

This module provides filtering capabilities to reduce response verbosity and 
optimize responses for LLM consumption while maintaining the exact same 
YAML structure as the original Redmine API responses.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import copy


@dataclass
class FilterConfig:
    """Configuration for response filtering options."""
    include_fields: Optional[List[str]] = None      # Specific fields to include
    exclude_fields: Optional[List[str]] = None      # Specific fields to exclude  
    remove_empty: bool = False                      # Remove fields with empty/null values
    remove_custom_fields: bool = False              # Remove all custom fields
    keep_custom_fields: Optional[List[str]] = None  # Keep only specified custom fields
    max_description_length: Optional[int] = None    # Truncate long descriptions
    max_array_items: Optional[int] = None           # Limit array sizes


def apply_response_filter(response: dict, mcp_filter: dict) -> dict:
    """
    Apply filtering to a Redmine API response.
    
    Args:
        response: The response dict with status_code, body, error structure
        mcp_filter: Dictionary containing filter configuration
        
    Returns:
        Filtered response dict with same structure, mcp_filtered flag added
    """
    # Don't filter error responses
    if response.get("status_code", 0) != 200 or response.get("error"):
        return response
        
    # Create a deep copy to avoid modifying original
    filtered_response = copy.deepcopy(response)
    
    try:
        # Parse filter configuration
        config = FilterConfig(
            include_fields=mcp_filter.get("include_fields"),
            exclude_fields=mcp_filter.get("exclude_fields"),
            remove_empty=mcp_filter.get("remove_empty", False),
            remove_custom_fields=mcp_filter.get("remove_custom_fields", False),
            keep_custom_fields=mcp_filter.get("keep_custom_fields"),
            max_description_length=mcp_filter.get("max_description_length"),
            max_array_items=mcp_filter.get("max_array_items")
        )
        
        # Apply filtering to the response body
        if filtered_response.get("body"):
            filtered_response["body"] = filter_data(filtered_response["body"], config)
            
        # Add indicator that filtering was applied
        filtered_response["mcp_filtered"] = True
        
        return filtered_response
        
    except Exception:
        # On any filtering error, return original response
        return response


def filter_data(data: Any, config: FilterConfig) -> Any:
    """
    Recursively filter data based on configuration.
    
    Args:
        data: Data to filter (dict, list, or primitive)
        config: Filter configuration
        
    Returns:
        Filtered data maintaining original structure
    """
    if isinstance(data, dict):
        return filter_dict(data, config)
    elif isinstance(data, list):
        return filter_list(data, config)
    else:
        return data


def filter_dict(data: dict, config: FilterConfig) -> dict:
    """Filter a dictionary based on configuration."""
    filtered = {}
    
    for key, value in data.items():
        # Skip empty values if configured
        if config.remove_empty and is_empty_value(value):
            continue
            
        # Handle custom_fields specially
        if key == "custom_fields" and isinstance(value, list):
            if config.remove_custom_fields:
                continue
            elif config.keep_custom_fields:
                filtered_custom_fields = filter_custom_fields(value, config.keep_custom_fields)
                if filtered_custom_fields:  # Only include if not empty
                    filtered[key] = filtered_custom_fields
                continue
                
        # Apply include/exclude field filtering
        if config.include_fields and key not in config.include_fields:
            continue
        if config.exclude_fields and key in config.exclude_fields:
            continue
            
        # Handle description field truncation
        if (key in ["description", "notes", "text"] and 
            isinstance(value, str) and 
            config.max_description_length and 
            len(value) > config.max_description_length):
            filtered[key] = value[:config.max_description_length] + "... [truncated]"
        else:
            # Recursively filter nested data
            filtered[key] = filter_data(value, config)
    
    return filtered


def filter_list(data: list, config: FilterConfig) -> list:
    """Filter a list based on configuration."""
    filtered = []
    
    for item in data:
        filtered_item = filter_data(item, config)
        
        # Skip empty items if configured
        if config.remove_empty and is_empty_value(filtered_item):
            continue
            
        filtered.append(filtered_item)
        
        # Limit array size if configured
        if config.max_array_items and len(filtered) >= config.max_array_items:
            break
    
    return filtered


def filter_custom_fields(custom_fields: List[dict], keep_fields: List[str]) -> List[dict]:
    """
    Filter custom fields to keep only specified ones.
    
    Args:
        custom_fields: List of custom field dictionaries
        keep_fields: List of custom field names to keep
        
    Returns:
        Filtered list of custom fields
    """
    filtered = []
    
    for field in custom_fields:
        field_name = field.get("name", "")
        if field_name in keep_fields:
            filtered.append(field)
    
    return filtered


def is_empty_value(value: Any) -> bool:
    """
    Check if a value should be considered empty for filtering purposes.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is considered empty
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def remove_empty_fields(data: Any) -> Any:
    """
    Recursively remove empty fields from data structure.
    
    Args:
        data: Data to clean
        
    Returns:
        Data with empty fields removed
    """
    config = FilterConfig(remove_empty=True)
    return filter_data(data, config)
