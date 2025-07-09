#!/usr/bin/env python3
"""Test script to verify JSON/YAML format support in mcp-redmine"""

import os
import sys
import json
import yaml

# Add the module path
sys.path.insert(0, os.path.dirname(__file__))

def test_format_response():
    """Test the format_response function with both YAML and JSON formats"""
    
    # Test data
    test_data = {
        "status_code": 200,
        "body": {
            "issues": [
                {"id": 1, "subject": "Test Issue 1"},
                {"id": 2, "subject": "Test Issue 2"}
            ]
        },
        "error": ""
    }
    
    # Test YAML format (default)
    os.environ['RESPONSE_FORMAT'] = 'yaml'
    from mcp_redmine.server import format_response, RESPONSE_FORMAT
    
    print("Testing YAML format (default):")
    print(f"RESPONSE_FORMAT: {RESPONSE_FORMAT}")
    yaml_result = format_response(test_data)
    print("Output:")
    print(yaml_result)
    print("-" * 50)
    
    # Verify it's valid YAML
    try:
        parsed_yaml = yaml.safe_load(yaml_result)
        print("✓ Valid YAML format")
    except Exception as e:
        print(f"✗ Invalid YAML: {e}")
    
    # Test JSON format
    os.environ['RESPONSE_FORMAT'] = 'json'
    # Reload module to pick up new environment variable
    import importlib
    import mcp_redmine.server
    importlib.reload(mcp_redmine.server)
    from mcp_redmine.server import format_response, RESPONSE_FORMAT
    
    print("\nTesting JSON format:")
    print(f"RESPONSE_FORMAT: {RESPONSE_FORMAT}")
    json_result = format_response(test_data)
    print("Output:")
    print(json_result)
    print("-" * 50)
    
    # Verify it's valid JSON
    try:
        parsed_json = json.loads(json_result)
        print("✓ Valid JSON format")
    except Exception as e:
        print(f"✗ Invalid JSON: {e}")
    
    # Test with an edge case (datetime object)
    from datetime import datetime
    edge_case_data = {
        "timestamp": datetime.now(),
        "data": ["item1", "item2"]
    }
    
    print("\nTesting JSON format with datetime object:")
    json_result_edge = format_response(edge_case_data)
    print(json_result_edge)
    
    # Reset to default
    os.environ['RESPONSE_FORMAT'] = 'yaml'

if __name__ == "__main__":
    # Set required environment variables for the module to load
    os.environ.setdefault('REDMINE_URL', 'http://example.com')
    os.environ.setdefault('REDMINE_API_KEY', 'test_key')
    
    test_format_response()