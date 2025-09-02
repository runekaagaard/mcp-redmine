"""
Tests for MCP capabilities documentation functionality.
"""

import pytest
from mcp_redmine.mcp_capabilities import get_mcp_capabilities


class TestMcpCapabilities:
    """Test MCP capabilities documentation generation."""
    
    def test_get_mcp_capabilities_basic_structure(self):
        """Test that get_mcp_capabilities returns expected structure."""
        capabilities = get_mcp_capabilities("/test.json")
        
        # Should have top-level description
        assert "description" in capabilities
        assert isinstance(capabilities["description"], str)
        assert len(capabilities["description"]) > 0
        
        # Should have response_filtering section
        assert "response_filtering" in capabilities
        filtering = capabilities["response_filtering"]
        
        assert "description" in filtering
        assert "parameter" in filtering
        assert "usage" in filtering
        assert "options" in filtering
        
        assert filtering["parameter"] == "mcp_filter"
    
    def test_response_filtering_options(self):
        """Test that response filtering options are properly defined."""
        capabilities = get_mcp_capabilities("/test.json")
        options = capabilities["response_filtering"]["options"]
        
        # Check all expected options are present
        expected_options = [
            "remove_empty", "exclude_fields", "include_fields",
            "max_description_length", "max_array_items"
        ]
        
        for option in expected_options:
            assert option in options, f"Missing option: {option}"
            
            # Each option should have type and description
            assert "type" in options[option]
            assert "description" in options[option]
            assert "example" in options[option]
    
    def test_issues_path_specific_options(self):
        """Test that issues paths get additional filtering options."""
        capabilities = get_mcp_capabilities("/issues.json")
        options = capabilities["response_filtering"]["options"]
        
        # Issues paths should have custom field options
        assert "remove_custom_fields" in options
        assert "keep_custom_fields" in options
        
        # Check structure of custom field options
        assert options["remove_custom_fields"]["type"] == "boolean"
        assert options["remove_custom_fields"]["default"] is False
        
        assert options["keep_custom_fields"]["type"] == "array"
        assert "Build" in options["keep_custom_fields"]["example"]
    
    def test_non_issues_path_no_custom_field_options(self):
        """Test that non-issues paths don't get custom field options."""
        capabilities = get_mcp_capabilities("/projects.json")
        options = capabilities["response_filtering"]["options"]
        
        # Non-issues paths should NOT have custom field options
        assert "remove_custom_fields" not in options
        assert "keep_custom_fields" not in options
    
    def test_option_types_and_examples(self):
        """Test that all options have correct types and examples."""
        capabilities = get_mcp_capabilities("/issues.json")
        options = capabilities["response_filtering"]["options"]
        
        # Boolean options
        boolean_options = ["remove_empty", "remove_custom_fields"]
        for option in boolean_options:
            if option in options:
                assert options[option]["type"] == "boolean"
                assert isinstance(options[option]["example"], bool)
        
        # Array options
        array_options = ["exclude_fields", "include_fields", "keep_custom_fields"]
        for option in array_options:
            if option in options:
                assert options[option]["type"] == "array"
                assert isinstance(options[option]["example"], list)
        
        # Integer options
        integer_options = ["max_description_length", "max_array_items"]
        for option in integer_options:
            if option in options:
                assert options[option]["type"] == "integer"
                assert isinstance(options[option]["example"], int)
    
    def test_descriptions_are_meaningful(self):
        """Test that all descriptions provide meaningful information."""
        capabilities = get_mcp_capabilities("/issues.json")
        
        # Top-level description
        assert "MCP server" in capabilities["description"]
        
        # Response filtering description
        filtering = capabilities["response_filtering"]
        assert "response size" in filtering["description"].lower()
        
        # Usage instruction
        assert "mcp_filter" in filtering["usage"]
        assert "redmine_request" in filtering["usage"]
        
        # Option descriptions should be descriptive
        for option_name, option_config in filtering["options"].items():
            description = option_config["description"]
            assert len(description) > 10, f"Description too short for {option_name}"
            assert description[0].isupper(), f"Description should start with capital for {option_name}"
    
    def test_path_parameter_handling(self):
        """Test that different path parameters are handled correctly."""
        # Test various path formats
        test_paths = [
            "/issues.json",
            "/issues/{id}.json", 
            "/projects.json",
            "/users.json",
            "/custom_fields.json"
        ]
        
        for path in test_paths:
            capabilities = get_mcp_capabilities(path)
            
            # All paths should have basic structure
            assert "description" in capabilities
            assert "response_filtering" in capabilities
            
            # Only issues-related paths should have custom field options
            options = capabilities["response_filtering"]["options"]
            if "issues" in path:
                assert "remove_custom_fields" in options
                assert "keep_custom_fields" in options
            else:
                assert "remove_custom_fields" not in options
                assert "keep_custom_fields" not in options


    def test_preset_integration(self):
        """Test that presets are properly integrated into capabilities."""
        capabilities = get_mcp_capabilities("/issues.json")
        
        # Should have presets section under response_filtering
        assert "presets" in capabilities["response_filtering"]
        presets_section = capabilities["response_filtering"]["presets"]
        
        # Should have proper structure
        assert "description" in presets_section
        assert "usage" in presets_section
        assert "available_presets" in presets_section
        
        # Should contain all expected presets
        available_presets = presets_section["available_presets"]
        expected_presets = ["minimal", "clean", "essential_issues", "essential_projects", "summary", "no_custom_fields"]
        
        for preset in expected_presets:
            assert preset in available_presets, f"Missing preset: {preset}"
            assert isinstance(available_presets[preset], str), f"Preset {preset} should have string description"
            assert len(available_presets[preset]) > 0, f"Preset {preset} should have non-empty description"


if __name__ == "__main__":
    pytest.main([__file__])
