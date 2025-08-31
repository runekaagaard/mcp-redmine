"""
Predefined filter configurations for common use cases.

This module provides ready-to-use filter configurations that address
common scenarios for reducing Redmine API response verbosity.
"""

from typing import Dict, Any


def get_preset_filters() -> Dict[str, Dict[str, Any]]:
    """
    Get all available preset filter configurations.
    
    Returns:
        Dictionary mapping preset names to filter configurations
    """
    return {
        "minimal": get_minimal_preset(),
        "clean": get_clean_preset(), 
        "essential_issues": get_essential_issues_preset(),
        "essential_projects": get_essential_projects_preset(),
        "summary": get_summary_preset(),
        "no_custom_fields": get_no_custom_fields_preset()
    }


def get_minimal_preset() -> Dict[str, Any]:
    """
    Minimal preset - remove noise and keep essential data.
    
    Returns:
        Filter configuration for minimal responses
    """
    return {
        "remove_empty": True,
        "remove_custom_fields": True,
        "max_description_length": 100
    }


def get_clean_preset() -> Dict[str, Any]:
    """
    Clean preset - remove empty fields and limit arrays.
    
    Returns:
        Filter configuration for clean responses
    """
    return {
        "remove_empty": True,
        "max_array_items": 10,
        "max_description_length": 500
    }


def get_essential_issues_preset() -> Dict[str, Any]:
    """
    Essential issues preset - key issue fields only.
    
    Returns:
        Filter configuration for essential issue information
    """
    return {
        "remove_empty": True,
        "remove_custom_fields": True,
        "max_description_length": 300,
        "exclude_fields": ["journals", "changesets", "attachments", "watchers"]
    }


def get_essential_projects_preset() -> Dict[str, Any]:
    """
    Essential projects preset - key project fields only.
    
    Returns:
        Filter configuration for essential project information
    """
    return {
        "remove_empty": True,
        "remove_custom_fields": True,
        "max_description_length": 200,
        "exclude_fields": ["trackers", "issue_categories", "enabled_modules"]
    }


def get_summary_preset() -> Dict[str, Any]:
    """
    Summary preset - condensed view with limited details.
    
    Returns:
        Filter configuration for summary responses
    """
    return {
        "remove_empty": True,
        "remove_custom_fields": True,
        "max_description_length": 150,
        "max_array_items": 5,
        "exclude_fields": ["journals", "changesets", "attachments"]
    }


def get_no_custom_fields_preset() -> Dict[str, Any]:
    """
    No custom fields preset - remove all custom field noise.
    
    Returns:
        Filter configuration removing custom fields
    """
    return {
        "remove_custom_fields": True,
        "remove_empty": True
    }


def get_preset_documentation() -> Dict[str, str]:
    """
    Get documentation for all preset filters.
    
    Returns:
        Dictionary mapping preset names to descriptions
    """
    return {
        "minimal": "Remove custom fields, empty values, truncate to 100 chars",
        "clean": "Remove empty fields, limit arrays to 10, truncate to 500 chars",
        "essential_issues": "Remove custom fields, journals, attachments, watchers, truncate to 300 chars",
        "essential_projects": "Remove custom fields, trackers, categories, modules, truncate to 200 chars", 
        "summary": "Remove custom fields, journals, attachments, truncate to 150 chars, limit arrays to 5",
        "no_custom_fields": "Remove custom fields and empty values only"
    }


def apply_preset(preset_name: str) -> Dict[str, Any]:
    """
    Get a specific preset filter configuration.
    
    Args:
        preset_name: Name of the preset to retrieve
        
    Returns:
        Filter configuration dictionary
        
    Raises:
        ValueError: If preset name is not found
    """
    presets = get_preset_filters()
    
    if preset_name not in presets:
        available = ", ".join(presets.keys())
        raise ValueError(f"Unknown preset '{preset_name}'. Available presets: {available}")
    
    return presets[preset_name]
