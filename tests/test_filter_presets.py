"""
Tests for filter presets functionality.
"""

import pytest
from mcp_redmine.filter_presets import (
    get_preset_filters,
    get_preset_documentation,
    apply_preset,
    get_minimal_preset,
    get_clean_preset,
    get_essential_issues_preset,
    get_essential_projects_preset,
    get_summary_preset,
    get_no_custom_fields_preset
)


class TestPresetRetrieval:
    """Test preset retrieval functions."""
    
    def test_get_preset_filters_returns_all_presets(self):
        presets = get_preset_filters()
        
        expected_presets = {
            "minimal", "clean", "essential_issues", 
            "essential_projects", "summary", "no_custom_fields"
        }
        assert set(presets.keys()) == expected_presets
    
    def test_get_preset_documentation_has_all_presets(self):
        docs = get_preset_documentation()
        presets = get_preset_filters()
        
        # Documentation should cover all presets
        assert set(docs.keys()) == set(presets.keys())
        
        # All documentation should be non-empty strings
        for preset_name, description in docs.items():
            assert isinstance(description, str)
            assert len(description) > 0


class TestApplyPreset:
    """Test preset application."""
    
    def test_apply_valid_preset(self):
        result = apply_preset("minimal")
        expected = get_minimal_preset()
        assert result == expected
    
    def test_apply_invalid_preset_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            apply_preset("nonexistent_preset")
        
        assert "Unknown preset 'nonexistent_preset'" in str(exc_info.value)
        assert "Available presets:" in str(exc_info.value)


class TestIndividualPresets:
    """Test individual preset configurations."""
    
    def test_minimal_preset(self):
        preset = get_minimal_preset()
        
        assert "remove_empty" in preset
        assert "remove_custom_fields" in preset
        assert "max_description_length" in preset
        
        assert preset["remove_empty"] is True
        assert preset["remove_custom_fields"] is True
        assert preset["max_description_length"] == 100
    
    def test_clean_preset(self):
        preset = get_clean_preset()
        
        assert preset["remove_empty"] is True
        assert "max_array_items" in preset
        assert "max_description_length" in preset
        assert preset["max_array_items"] == 10
        assert preset["max_description_length"] == 500
    
    def test_essential_issues_preset(self):
        preset = get_essential_issues_preset()
        
        assert preset["remove_empty"] is True
        assert preset["remove_custom_fields"] is True
        assert preset["max_description_length"] == 300
        assert "exclude_fields" in preset
        
        # Should exclude verbose fields
        excluded_fields = ["journals", "changesets", "attachments", "watchers"]
        assert preset["exclude_fields"] == excluded_fields
    
    def test_essential_projects_preset(self):
        preset = get_essential_projects_preset()
        
        assert preset["remove_empty"] is True
        assert preset["remove_custom_fields"] is True
        assert preset["max_description_length"] == 200
        assert "exclude_fields" in preset
        
        # Should exclude verbose fields
        excluded_fields = ["trackers", "issue_categories", "enabled_modules"]
        assert preset["exclude_fields"] == excluded_fields
    
    def test_summary_preset(self):
        preset = get_summary_preset()
        
        assert preset["remove_empty"] is True
        assert preset["remove_custom_fields"] is True
        assert preset["max_description_length"] == 150
        assert preset["max_array_items"] == 5
        
        # Should exclude verbose fields
        excluded_fields = ["journals", "changesets", "attachments"]
        assert preset["exclude_fields"] == excluded_fields
    
    def test_no_custom_fields_preset(self):
        preset = get_no_custom_fields_preset()
        
        assert preset["remove_custom_fields"] is True
        assert preset["remove_empty"] is True


class TestPresetIntegration:
    """Test preset integration with filtering system."""
    
    def test_all_presets_are_valid_filter_configs(self):
        """Ensure all presets contain valid filter configuration keys."""
        presets = get_preset_filters()
        
        valid_keys = {
            "include_fields", "exclude_fields", "remove_empty",
            "remove_custom_fields", "keep_custom_fields", 
            "max_description_length", "max_array_items"
        }
        
        for preset_name, preset_config in presets.items():
            for key in preset_config.keys():
                assert key in valid_keys, f"Invalid key '{key}' in preset '{preset_name}'"
    
    def test_preset_consistency(self):
        """Test that presets are internally consistent."""
        presets = get_preset_filters()
        
        for preset_name, preset_config in presets.items():
            # If include_fields is specified, it should be a non-empty list
            if "include_fields" in preset_config:
                assert isinstance(preset_config["include_fields"], list)
                assert len(preset_config["include_fields"]) > 0
            
            # If exclude_fields is specified, it should be a non-empty list
            if "exclude_fields" in preset_config:
                assert isinstance(preset_config["exclude_fields"], list)
                assert len(preset_config["exclude_fields"]) > 0
            
            # Numeric limits should be positive
            if "max_description_length" in preset_config:
                assert preset_config["max_description_length"] > 0
            
            if "max_array_items" in preset_config:
                assert preset_config["max_array_items"] > 0
    
    def test_preset_names_match_functions(self):
        """Ensure preset names match their getter function names."""
        presets = get_preset_filters()
        
        # Map preset names to their expected getter functions
        expected_functions = {
            "minimal": get_minimal_preset,
            "clean": get_clean_preset,
            "essential_issues": get_essential_issues_preset,
            "essential_projects": get_essential_projects_preset,
            "summary": get_summary_preset,
            "no_custom_fields": get_no_custom_fields_preset
        }
        
        for preset_name in presets.keys():
            assert preset_name in expected_functions, f"No getter function for preset '{preset_name}'"
            
            # Verify the preset matches its getter function
            preset_from_dict = presets[preset_name]
            preset_from_function = expected_functions[preset_name]()
            assert preset_from_dict == preset_from_function


class TestPresetDocumentation:
    """Test preset documentation quality."""
    
    def test_documentation_describes_functionality(self):
        """Ensure documentation describes what each preset does."""
        docs = get_preset_documentation()
        
        # Minimal should mention custom fields or empty values
        assert any(word in docs["minimal"].lower() 
                  for word in ["custom", "empty", "remove"])
        
        # Clean should mention empty fields or arrays
        assert any(word in docs["clean"].lower() 
                  for word in ["empty", "array", "limit"])
        
        # Summary should mention condensed/no custom fields
        assert any(word in docs["summary"].lower() 
                  for word in ["condensed", "custom", "no"])
        
        # No custom fields should mention custom fields
        assert "custom" in docs["no_custom_fields"].lower()


if __name__ == "__main__":
    pytest.main([__file__])
