"""
Response filtering and transformation utilities for Redmine MCP server.

This module provides filtering capabilities to reduce response verbosity and 
optimize responses for LLM consumption while maintaining the exact same 
YAML structure as the original Redmine API responses.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import copy
import re
from mcp.server.fastmcp.utilities.logging import get_logger

# Import journal filtering capabilities
from .journal_filters import JournalFilterConfig, JournalFilterProcessor, filter_journals_for_code_review

logger = get_logger(__name__)


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
    journals: Optional[JournalFilterConfig] = None  # Journal filtering configuration


def validate_filter_config(mcp_filter: dict) -> List[str]:
    """
    Validate MCP filter configuration and return list of validation errors.
    
    Args:
        mcp_filter: Dictionary containing filter configuration
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Validate journal filter configuration
    if "journals" in mcp_filter:
        journals_config = mcp_filter["journals"]
        if not isinstance(journals_config, dict):
            errors.append("journals filter must be a dictionary")
        else:
            # Validate journal filter options
            valid_journal_options = {"code_review_only"}
            for key in journals_config.keys():
                if key not in valid_journal_options:
                    errors.append(f"Invalid journal filter option: {key}. Valid options: {valid_journal_options}")
            
            # Validate code_review_only type
            if "code_review_only" in journals_config:
                if not isinstance(journals_config["code_review_only"], bool):
                    errors.append("code_review_only must be a boolean value")
    
    # Validate other filter options
    if "max_description_length" in mcp_filter:
        if not isinstance(mcp_filter["max_description_length"], int) or mcp_filter["max_description_length"] <= 0:
            errors.append("max_description_length must be a positive integer")
    
    if "max_array_items" in mcp_filter:
        if not isinstance(mcp_filter["max_array_items"], int) or mcp_filter["max_array_items"] <= 0:
            errors.append("max_array_items must be a positive integer")
    
    if "include_fields" in mcp_filter:
        if not isinstance(mcp_filter["include_fields"], list):
            errors.append("include_fields must be a list of strings")
        elif not all(isinstance(x, str) for x in mcp_filter["include_fields"]):
            errors.append("include_fields list items must be strings")
    
    if "exclude_fields" in mcp_filter:
        if not isinstance(mcp_filter["exclude_fields"], list):
            errors.append("exclude_fields must be a list of strings")
        elif not all(isinstance(x, str) for x in mcp_filter["exclude_fields"]):
            errors.append("exclude_fields list items must be strings")
    
    if "keep_custom_fields" in mcp_filter:
        if not isinstance(mcp_filter["keep_custom_fields"], list):
            errors.append("keep_custom_fields must be a list of strings")
        elif not all(isinstance(x, str) for x in mcp_filter["keep_custom_fields"]):
            errors.append("keep_custom_fields list items must be strings")
    
    # Validate boolean options
    for key in ("remove_empty", "remove_custom_fields"):
        if key in mcp_filter and not isinstance(mcp_filter[key], bool):
            errors.append(f"{key} must be a boolean value")
    
    return errors


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
        # Validate filter configuration
        validation_errors = validate_filter_config(mcp_filter)
        if validation_errors:
            logger.warning(f"Invalid journal filter syntax: {validation_errors}")
            # Still set mcp_filtered flag even with validation errors
            filtered_response["mcp_filtered"] = True
            return filtered_response
        
        # Parse filter configuration
        journals_config = None
        if "journals" in mcp_filter:
            journals_dict = mcp_filter["journals"]
            if isinstance(journals_dict, dict):
                journals_config = JournalFilterConfig(
                    code_review_only=journals_dict.get("code_review_only", False)
                )
            else:
                # Log warning for invalid journal filter syntax
                logger.warning(f"Invalid journal filter syntax: expected dict, got {type(journals_dict)}")
        
        config = FilterConfig(
            include_fields=mcp_filter.get("include_fields"),
            exclude_fields=mcp_filter.get("exclude_fields"),
            remove_empty=mcp_filter.get("remove_empty", False),
            remove_custom_fields=mcp_filter.get("remove_custom_fields", False),
            keep_custom_fields=mcp_filter.get("keep_custom_fields"),
            max_description_length=mcp_filter.get("max_description_length"),
            max_array_items=mcp_filter.get("max_array_items"),
            journals=journals_config
        )
        
        # Apply filtering to the response body
        if filtered_response.get("body"):
            filtered_response["body"] = filter_data(filtered_response["body"], config)
            
        # Add indicator that filtering was applied
        filtered_response["mcp_filtered"] = True
        
        return filtered_response
        
    except Exception as e:
        # Log warning for filtering errors but return original response to maintain backward compatibility
        logger.warning(f"Response filtering failed: {e}")
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
        
        # Apply include/exclude field filtering, but handle Redmine response structure
        if config.include_fields:
            # Always include wrapper keys and filter their contents
            if key in ["issue", "issues", "projects", "users", "time_entries"]:
                pass
            elif key not in config.include_fields:
                continue
        # include_fields overrides exclude_fields by design
        if (not config.include_fields) and config.exclude_fields and key in config.exclude_fields:
            continue

        # Handle journals filtering after field exclusion rules
        if key == "journals" and isinstance(value, list) and config.journals:
            try:
                processor = JournalFilterProcessor()
                filtered_journals = processor.filter_journals(value, config.journals)
                filtered[key] = filtered_journals
            except (re.error, TypeError, AttributeError, KeyError) as e:
                logger.warning(f"Journal filtering failed, returning unfiltered journals: {e}")
                filtered[key] = value
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
