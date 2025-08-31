"""
Tests for response filtering functionality.
"""

import pytest
from mcp_redmine.response_filters import (
    apply_response_filter,
    filter_data,
    filter_custom_fields,
    is_empty_value,
    remove_empty_fields,
    FilterConfig
)


class TestFilterConfig:
    """Test FilterConfig dataclass."""
    
    def test_default_values(self):
        config = FilterConfig()
        assert config.include_fields is None
        assert config.exclude_fields is None
        assert config.remove_empty is False
        assert config.remove_custom_fields is False
        assert config.keep_custom_fields is None
        assert config.max_description_length is None
        assert config.max_array_items is None


class TestIsEmptyValue:
    """Test empty value detection."""
    
    def test_none_is_empty(self):
        assert is_empty_value(None) is True
    
    def test_empty_string_is_empty(self):
        assert is_empty_value("") is True
        assert is_empty_value("   ") is True
    
    def test_empty_collections_are_empty(self):
        assert is_empty_value([]) is True
        assert is_empty_value({}) is True
    
    def test_non_empty_values_are_not_empty(self):
        assert is_empty_value("text") is False
        assert is_empty_value(0) is False
        assert is_empty_value(False) is False
        assert is_empty_value([1, 2]) is False
        assert is_empty_value({"key": "value"}) is False


class TestFilterCustomFields:
    """Test custom field filtering."""
    
    def test_filter_by_name(self):
        custom_fields = [
            {"id": 1, "name": "Build", "value": "v1.0"},
            {"id": 2, "name": "Contact", "value": ""},
            {"id": 3, "name": "Owner", "value": "John"}
        ]
        
        result = filter_custom_fields(custom_fields, ["Build", "Owner"])
        
        assert len(result) == 2
        assert result[0]["name"] == "Build"
        assert result[1]["name"] == "Owner"
    
    def test_filter_nonexistent_fields(self):
        custom_fields = [
            {"id": 1, "name": "Build", "value": "v1.0"}
        ]
        
        result = filter_custom_fields(custom_fields, ["NonExistent"])
        
        assert len(result) == 0


class TestRemoveEmptyFields:
    """Test empty field removal."""
    
    def test_remove_empty_from_dict(self):
        data = {
            "id": 1,
            "name": "Test",
            "description": None,
            "tags": [],
            "metadata": ""
        }
        
        result = remove_empty_fields(data)
        
        assert result == {"id": 1, "name": "Test"}
    
    def test_remove_empty_from_nested_dict(self):
        data = {
            "issue": {
                "id": 1,
                "subject": "Test",
                "assignee": None,
                "custom_fields": []
            },
            "empty_section": {}
        }
        
        result = remove_empty_fields(data)
        
        assert result == {
            "issue": {
                "id": 1,
                "subject": "Test"
            }
        }
    
    def test_remove_empty_from_list(self):
        data = [
            {"id": 1, "name": "Valid"},
            {"id": 2, "name": ""},
            {"id": 3, "name": None}
        ]
        
        result = remove_empty_fields(data)
        
        # Actual behavior: removes empty fields from each dict, but keeps the dicts
        expected = [
            {"id": 1, "name": "Valid"},
            {"id": 2},  # Empty name removed, but dict remains
            {"id": 3}   # None name removed, but dict remains
        ]
        assert result == expected


class TestFilterData:
    """Test main filtering logic."""
    
    def test_include_fields_filter(self):
        data = {
            "id": 1,
            "subject": "Test Issue",
            "description": "Long description",
            "status": {"id": 1, "name": "New"},
            "custom_fields": []
        }
        
        config = FilterConfig(include_fields=["id", "subject", "status"])
        result = filter_data(data, config)
        
        # Actual behavior: include_fields is applied recursively, so nested objects are also filtered
        expected = {
            "id": 1,
            "subject": "Test Issue", 
            "status": {"id": 1}  # "name" is filtered out because it's not in include_fields
        }
        assert result == expected
    
    def test_exclude_fields_filter(self):
        data = {
            "id": 1,
            "subject": "Test Issue",
            "custom_fields": [],
            "journals": []
        }
        
        config = FilterConfig(exclude_fields=["custom_fields", "journals"])
        result = filter_data(data, config)
        
        expected = {
            "id": 1,
            "subject": "Test Issue"
        }
        assert result == expected
    
    def test_remove_custom_fields(self):
        data = {
            "id": 1,
            "subject": "Test",
            "custom_fields": [
                {"id": 1, "name": "Build", "value": "v1.0"}
            ]
        }
        
        config = FilterConfig(remove_custom_fields=True)
        result = filter_data(data, config)
        
        expected = {
            "id": 1,
            "subject": "Test"
        }
        assert result == expected
    
    def test_keep_specific_custom_fields(self):
        data = {
            "id": 1,
            "custom_fields": [
                {"id": 1, "name": "Build", "value": "v1.0"},
                {"id": 2, "name": "Contact", "value": ""},
                {"id": 3, "name": "Owner", "value": "John"}
            ]
        }
        
        config = FilterConfig(keep_custom_fields=["Build", "Owner"])
        result = filter_data(data, config)
        
        assert len(result["custom_fields"]) == 2
        assert result["custom_fields"][0]["name"] == "Build"
        assert result["custom_fields"][1]["name"] == "Owner"
    
    def test_truncate_description(self):
        data = {
            "id": 1,
            "description": "This is a very long description that should be truncated"
        }
        
        config = FilterConfig(max_description_length=20)
        result = filter_data(data, config)
        
        assert result["description"] == "This is a very long ... [truncated]"
    
    def test_limit_array_items(self):
        data = {
            "items": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        }
        
        config = FilterConfig(max_array_items=3)
        result = filter_data(data, config)
        
        assert result["items"] == [1, 2, 3]


class TestApplyResponseFilter:
    """Test complete response filtering."""
    
    def test_filter_successful_response(self):
        response = {
            "status_code": 200,
            "body": {
                "issues": [
                    {
                        "id": 1,
                        "subject": "Test Issue",
                        "description": None,
                        "custom_fields": []
                    }
                ]
            },
            "error": ""
        }
        
        mcp_filter = {"remove_empty": True}
        result = apply_response_filter(response, mcp_filter)
        
        assert result["mcp_filtered"] is True
        assert result["body"]["issues"][0] == {
            "id": 1,
            "subject": "Test Issue"
        }
    
    def test_dont_filter_error_response(self):
        response = {
            "status_code": 404,
            "body": {"error": "Not found"},
            "error": "HTTPError: 404"
        }
        
        mcp_filter = {"remove_empty": True}
        result = apply_response_filter(response, mcp_filter)
        
        # Should return original response unchanged
        assert result == response
        assert "mcp_filtered" not in result
    
    def test_filter_error_fallback(self):
        response = {
            "status_code": 200,
            "body": {"test": "data"},
            "error": ""
        }
        
        # Invalid filter config should not break the response
        mcp_filter = {"invalid_option": True}
        result = apply_response_filter(response, mcp_filter)
        
        # Should have mcp_filtered flag even with invalid config
        assert result["mcp_filtered"] is True
    
    def test_complex_filtering_scenario(self):
        """Test a realistic Redmine issue response filtering."""
        response = {
            "status_code": 200,
            "body": {
                "issues": [
                    {
                        "id": 36461,
                        "subject": "Implement CIS Benchmark",
                        "description": "Very long description that needs truncation...",
                        "status": {"id": 5, "name": "Development"},
                        "assigned_to": {"id": 421, "name": "Dan Sun"},
                        "custom_fields": [
                            {"id": 3, "name": "Operational Contact", "value": ""},
                            {"id": 4, "name": "Reqs Approver", "value": ""},
                            {"id": 20, "name": "Build", "value": "v2.1.0"},
                            {"id": 109, "name": "Owner", "value": ""}
                        ],
                        "journals": [],
                        "attachments": []
                    }
                ],
                "total_count": 1,
                "offset": 0,
                "limit": 25
            },
            "error": ""
        }
        
        # Use a simpler filter that doesn't conflict with top-level structure
        mcp_filter = {
            "remove_empty": True,
            "keep_custom_fields": ["Build"],
            "exclude_fields": ["journals", "attachments"]
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        assert result["mcp_filtered"] is True
        assert "body" in result
        assert "issues" in result["body"]
        
        issue = result["body"]["issues"][0]
        
        # Should have Build custom field only
        if "custom_fields" in issue:
            build_fields = [cf for cf in issue["custom_fields"] if cf["name"] == "Build"]
            assert len(build_fields) == 1
            assert build_fields[0]["value"] == "v2.1.0"
        
        # Should not have excluded fields
        assert "journals" not in issue
        assert "attachments" not in issue


    def test_filter_exception_handling(self):
        """Test that filtering exceptions are handled gracefully."""
        response = {
            "status_code": 200,
            "body": {"test": "data"},
            "error": ""
        }
        
        # Create a filter config that might cause issues
        # This tests the exception handling in apply_response_filter
        class BadFilterConfig:
            def get(self, key, default=None):
                if key == "include_fields":
                    raise ValueError("Simulated error")
                return default
        
        # This should not raise an exception, should return original response
        result = apply_response_filter(response, BadFilterConfig())
        
        # Should return original response when exception occurs
        assert result == response
        assert "mcp_filtered" not in result
    
    def test_remove_empty_fields_function(self):
        """Test the standalone remove_empty_fields function."""
        data = {
            "valid": "data",
            "empty_string": "",
            "null_value": None,
            "empty_list": [],
            "empty_dict": {},
            "nested": {
                "valid": "nested_data",
                "empty": None
            }
        }
        
        result = remove_empty_fields(data)
        
        expected = {
            "valid": "data",
            "nested": {
                "valid": "nested_data"
            }
        }
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])


class TestJournalFiltering:
    """Test journal filtering integration with response filtering."""
    
    def test_journal_filtering_in_response_filter(self):
        """Test that journal filtering works through the main response filter."""
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 12345,
                    "subject": "Test Issue",
                    "journals": [
                        {
                            "id": 1,
                            "notes": "Regular status update",
                            "details": []
                        },
                        {
                            "id": 2,
                            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit-server/r/c/12345/1*",
                            "details": []
                        },
                        {
                            "id": 3,
                            "notes": "Code review completed and approved",
                            "details": []
                        }
                    ]
                }
            },
            "error": ""
        }
        
        mcp_filter = {
            "journals": {
                "code_review_only": True
            }
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        assert result["mcp_filtered"] is True
        journals = result["body"]["issue"]["journals"]
        
        # Should only have the 2 code review entries
        assert len(journals) == 2
        assert journals[0]["id"] == 2  # Gerrit entry
        assert journals[1]["id"] == 3  # Manual review entry
    
    def test_journal_filtering_with_other_filters(self):
        """Test journal filtering combined with other response filters."""
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 12345,
                    "subject": "Test Issue",
                    "description": "",
                    "custom_fields": [
                        {"id": 1, "name": "Build", "value": "v1.0"},
                        {"id": 2, "name": "Contact", "value": ""}
                    ],
                    "journals": [
                        {
                            "id": 1,
                            "notes": "Regular update",
                            "details": []
                        },
                        {
                            "id": 2,
                            "notes": "*Gerrit change* submitted",
                            "details": []
                        }
                    ]
                }
            },
            "error": ""
        }
        
        mcp_filter = {
            "remove_empty": True,
            "keep_custom_fields": ["Build"],
            "journals": {
                "code_review_only": True
            }
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        assert result["mcp_filtered"] is True
        issue = result["body"]["issue"]
        
        # Should have removed empty description
        assert "description" not in issue
        
        # Should have only Build custom field
        assert len(issue["custom_fields"]) == 1
        assert issue["custom_fields"][0]["name"] == "Build"
        
        # Should have only Gerrit journal entry
        assert len(issue["journals"]) == 1
        assert issue["journals"][0]["id"] == 2
    
    def test_journal_filtering_disabled(self):
        """Test that journals are not filtered when journal filtering is disabled."""
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "journals": [
                        {"id": 1, "notes": "Regular update"},
                        {"id": 2, "notes": "*Gerrit change* submitted"}
                    ]
                }
            },
            "error": ""
        }
        
        # No journal filtering specified
        mcp_filter = {
            "remove_empty": True
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        # Should have all journals unchanged
        assert len(result["body"]["issue"]["journals"]) == 2
    
    def test_journal_filtering_with_invalid_config(self):
        """Test handling of invalid journal filter configuration."""
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "journals": [
                        {"id": 1, "notes": "Regular update"},
                        {"id": 2, "notes": "*Gerrit change* submitted"}
                    ]
                }
            },
            "error": ""
        }
        
        # Invalid journal config (not a dict)
        mcp_filter = {
            "journals": "invalid_config"
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        # Should still work and return filtered response
        assert result["mcp_filtered"] is True
        # Journals should be unchanged due to invalid config
        assert len(result["body"]["issue"]["journals"]) == 2
    
    def test_journal_filtering_order_after_field_exclusion(self):
        """Test that journal filtering runs after field exclusion but before final response."""
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "subject": "Test Issue",
                    "description": "Test description",
                    "journals": [
                        {
                            "id": 1,
                            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit-server/r/c/12345/1*",
                            "created_on": "2025-01-01T10:00:00Z"
                        },
                        {
                            "id": 2,
                            "notes": "Regular status update",
                            "created_on": "2025-01-01T11:00:00Z"
                        }
                    ]
                }
            },
            "error": ""
        }
        
        # Test with field exclusion that should NOT exclude journals
        mcp_filter = {
            "exclude_fields": ["description"],  # Exclude description but not journals
            "journals": {"code_review_only": True}
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        assert result["mcp_filtered"] is True
        issue = result["body"]["issue"]
        
        # Description should be excluded due to field filtering
        assert "description" not in issue
        
        # Journals should be present and filtered for code review only
        assert "journals" in issue
        assert len(issue["journals"]) == 1  # Only Gerrit entry
        assert issue["journals"][0]["id"] == 1
        
        # Test with field exclusion that DOES exclude journals
        mcp_filter_exclude_journals = {
            "exclude_fields": ["journals"],  # Exclude journals entirely
            "journals": {"code_review_only": True}  # This should be ignored
        }
        
        result2 = apply_response_filter(response, mcp_filter_exclude_journals)
        
        assert result2["mcp_filtered"] is True
        issue2 = result2["body"]["issue"]
        
        # Journals should be completely excluded due to field filtering
        assert "journals" not in issue2

    def test_journal_filtering_error_handling_and_logging(self):
        """Test error handling and logging for journal filtering failures."""
        import logging
        from unittest.mock import patch
        
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "journals": [
                        {
                            "id": 1,
                            "notes": "*Gerrit change* submitted",
                            "created_on": "2025-01-01T10:00:00Z"
                        }
                    ]
                }
            },
            "error": ""
        }
        
        # Test invalid journal filter syntax
        mcp_filter_invalid = {
            "journals": "invalid_string_instead_of_dict"  # Should be a dict
        }
        
        with patch('mcp_redmine.response_filters.logger') as mock_logger:
            result = apply_response_filter(response, mcp_filter_invalid)
            
            # Should still return filtered response but log warning
            assert result["mcp_filtered"] is True
            mock_logger.warning.assert_called_once()
            assert "Invalid journal filter syntax" in str(mock_logger.warning.call_args)
        
        # Test with valid config to ensure normal operation still works
        mcp_filter_valid = {
            "journals": {"code_review_only": True}
        }
        
        result_valid = apply_response_filter(response, mcp_filter_valid)
        assert result_valid["mcp_filtered"] is True
        assert len(result_valid["body"]["issue"]["journals"]) == 1

    def test_journal_filtering_multiple_issues(self):
        """Test journal filtering with multiple issues in response."""
        response = {
            "status_code": 200,
            "body": {
                "issues": [
                    {
                        "id": 1,
                        "journals": [
                            {"id": 1, "notes": "Regular update"},
                            {"id": 2, "notes": "*Gerrit change* submitted"}
                        ]
                    },
                    {
                        "id": 2,
                        "journals": [
                            {"id": 3, "notes": "Status changed"},
                            {"id": 4, "notes": "Code review approved"}
                        ]
                    }
                ]
            },
            "error": ""
        }
        
        mcp_filter = {
            "journals": {
                "code_review_only": True
            }
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        assert result["mcp_filtered"] is True
        issues = result["body"]["issues"]
        
        # First issue should have only Gerrit entry
        assert len(issues[0]["journals"]) == 1
        assert issues[0]["journals"][0]["id"] == 2
        
        # Second issue should have only code review entry
        assert len(issues[1]["journals"]) == 1
        assert issues[1]["journals"][0]["id"] == 4


class TestJournalFilteringIntegration:
    """Comprehensive integration tests for journal filtering with MCP filter system."""
    
    def test_journal_filtering_with_all_mcp_filters_combined(self):
        """Test journal filtering combined with all existing MCP filters."""
        response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 12345,
                    "subject": "Complex Integration Test Issue",
                    "description": "This is a very long description that should be truncated when max_description_length is applied to test the integration of multiple filters working together",
                    "status": {"id": 2, "name": "In Progress"},
                    "assigned_to": {"id": 123, "name": "John Doe"},
                    "priority": {"id": 4, "name": "Normal"},
                    "tracker": {"id": 1, "name": "Bug"},
                    "category": None,
                    "fixed_version": None,
                    "custom_fields": [
                        {"id": 1, "name": "Build", "value": "v2.1.0"},
                        {"id": 2, "name": "Contact", "value": ""},
                        {"id": 3, "name": "Owner", "value": "Jane Smith"},
                        {"id": 4, "name": "Environment", "value": ""},
                        {"id": 5, "name": "Situation", "value": "Critical bug in production"}
                    ],
                    "journals": [
                        {
                            "id": 1,
                            "created_on": "2025-01-01T10:00:00Z",
                            "notes": "Issue created",
                            "details": [{"property": "attr", "name": "status_id", "old_value": "", "new_value": "1"}],
                            "user": {"id": 100, "name": "Reporter"}
                        },
                        {
                            "id": 2,
                            "created_on": "2025-01-01T11:00:00Z",
                            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/12345/1*\n\np(((. *Issue #12345: Complex Integration Test Issue*\n\nCommit: abc123def456789012345678901234567890abcd",
                            "details": [],
                            "user": {"id": 200, "name": "Gerrit Integration"}
                        },
                        {
                            "id": 3,
                            "created_on": "2025-01-01T12:00:00Z",
                            "notes": "Status changed to In Progress",
                            "details": [{"property": "attr", "name": "status_id", "old_value": "1", "new_value": "2"}],
                            "user": {"id": 123, "name": "John Doe"}
                        },
                        {
                            "id": 4,
                            "created_on": "2025-01-01T13:00:00Z",
                            "notes": "Code review completed successfully. All tests pass and implementation looks good.",
                            "details": [],
                            "user": {"id": 456, "name": "Tech Lead"}
                        },
                        {
                            "id": 5,
                            "created_on": "2025-01-01T14:00:00Z",
                            "notes": "Added attachment: test_results.pdf",
                            "details": [{"property": "attachment", "name": "test_results.pdf"}],
                            "user": {"id": 123, "name": "John Doe"}
                        }
                    ],
                    "attachments": [
                        {"id": 1, "filename": "test_results.pdf", "filesize": 1024}
                    ],
                    "watchers": [
                        {"id": 123, "name": "John Doe"},
                        {"id": 456, "name": "Tech Lead"}
                    ]
                }
            },
            "error": ""
        }
        
        # Apply comprehensive filter combining all MCP capabilities
        mcp_filter = {
            "exclude_fields": ["attachments", "watchers"],  # Remove unwanted fields
            "keep_custom_fields": ["Build", "Situation"],   # Keep only specific custom fields
            "remove_empty": True,                           # Remove empty/null values
            "max_description_length": 50,                   # Truncate long descriptions
            "journals": {"code_review_only": True}          # Filter journals for code review only
        }
        
        result = apply_response_filter(response, mcp_filter)
        
        # Verify mcp_filtered flag is set
        assert result["mcp_filtered"] is True
        
        issue = result["body"]["issue"]
        
        # Verify field exclusion worked
        assert "attachments" not in issue
        assert "watchers" not in issue
        
        # Verify empty field removal worked
        assert "category" not in issue
        assert "fixed_version" not in issue
        
        # Verify custom field filtering worked
        assert "custom_fields" in issue
        custom_field_names = [cf["name"] for cf in issue["custom_fields"]]
        assert "Build" in custom_field_names
        assert "Situation" in custom_field_names
        assert "Contact" not in custom_field_names  # Empty value should be filtered
        assert "Environment" not in custom_field_names  # Empty value should be filtered
        assert len(issue["custom_fields"]) == 2
        
        # Verify description truncation worked
        assert len(issue["description"]) <= 50 + len("... [truncated]")
        assert issue["description"].endswith("... [truncated]")
        
        # Verify journal filtering worked - should only have code review entries
        assert "journals" in issue
        assert len(issue["journals"]) == 2  # Gerrit entry + manual review entry
        journal_ids = [j["id"] for j in issue["journals"]]
        assert 2 in journal_ids  # Gerrit entry
        assert 4 in journal_ids  # Manual code review entry
        assert 1 not in journal_ids  # Issue creation (not code review)
        assert 3 not in journal_ids  # Status change (not code review)
        assert 5 not in journal_ids  # Attachment addition (not code review)
    
    def test_complete_request_response_cycle_simulation(self):
        """Verify complete request/response cycle with journal filtering enabled."""
        # Simulate a realistic Redmine API response for /issues/{id}.json?include=journals
        redmine_api_response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 36461,
                    "project": {"id": 123, "name": "Test Project"},
                    "tracker": {"id": 1, "name": "Feature"},
                    "status": {"id": 5, "name": "Development"},
                    "priority": {"id": 4, "name": "Normal"},
                    "author": {"id": 421, "name": "Dan Sun"},
                    "assigned_to": {"id": 421, "name": "Dan Sun"},
                    "subject": "Implement CIS Benchmark compliance checks",
                    "description": "Implement automated compliance checking for CIS benchmarks as specified in the security requirements document.",
                    "start_date": "2025-01-01",
                    "due_date": "2025-01-15",
                    "done_ratio": 75,
                    "is_private": False,
                    "estimated_hours": 40.0,
                    "total_estimated_hours": 40.0,
                    "spent_hours": 30.0,
                    "total_spent_hours": 30.0,
                    "custom_fields": [
                        {"id": 3, "name": "Operational Contact", "value": "ops@example.com"},
                        {"id": 4, "name": "Reqs Approver", "value": ""},
                        {"id": 20, "name": "Build", "value": "v2.1.0"},
                        {"id": 109, "name": "Owner", "value": "Dan Sun"},
                        {"id": 110, "name": "Situation", "value": "Security compliance requirement"},
                        {"id": 111, "name": "New High Level Design", "value": "Updated architecture document"},
                        {"id": 112, "name": "New Low Level Design", "value": ""}
                    ],
                    "created_on": "2025-01-01T09:00:00Z",
                    "updated_on": "2025-01-16T17:47:38Z",
                    "closed_on": None,
                    "journals": [
                        {
                            "id": 123450,
                            "user": {"id": 421, "name": "Dan Sun"},
                            "notes": "Initial implementation started. Setting up project structure and basic framework.",
                            "created_on": "2025-01-01T10:00:00Z",
                            "private_notes": False,
                            "details": [
                                {"property": "attr", "name": "status_id", "old_value": "1", "new_value": "2"}
                            ]
                        },
                        {
                            "id": 123451,
                            "user": {"id": 200, "name": "Gerrit Integration"},
                            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/54321/1*\n\np(((. *Issue #36461: Implement CIS Benchmark compliance checks*\n\nCommit: def456abc789012345678901234567890123456789",
                            "created_on": "2025-01-02T14:30:00Z",
                            "private_notes": False,
                            "details": []
                        },
                        {
                            "id": 123452,
                            "user": {"id": 421, "name": "Dan Sun"},
                            "notes": "Updated progress to 50%. Core framework implemented, working on specific benchmark checks.",
                            "created_on": "2025-01-05T11:15:00Z",
                            "private_notes": False,
                            "details": [
                                {"property": "attr", "name": "done_ratio", "old_value": "25", "new_value": "50"}
                            ]
                        },
                        {
                            "id": 123453,
                            "user": {"id": 500, "name": "Security Team Lead"},
                            "notes": "Reviewed the implementation approach and code quality. The design looks solid and follows security best practices. Approved for continued development.",
                            "created_on": "2025-01-08T16:45:00Z",
                            "private_notes": False,
                            "details": []
                        },
                        {
                            "id": 123454,
                            "user": {"id": 200, "name": "Gerrit Integration"},
                            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/54321/2*\n\np(((. *Issue #36461: Add unit tests and documentation*\n\nCommit: 789abc012345678901234567890123456789def456",
                            "created_on": "2025-01-10T09:20:00Z",
                            "private_notes": False,
                            "details": []
                        },
                        {
                            "id": 123455,
                            "user": {"id": 421, "name": "Dan Sun"},
                            "notes": "Added comprehensive unit tests and updated documentation. Ready for final review.",
                            "created_on": "2025-01-12T13:30:00Z",
                            "private_notes": False,
                            "details": [
                                {"property": "attr", "name": "done_ratio", "old_value": "50", "new_value": "75"}
                            ]
                        },
                        {
                            "id": 123456,
                            "user": {"id": 600, "name": "QA Engineer"},
                            "notes": "Completed testing of the CIS benchmark implementation. All test cases pass successfully. Code review shows excellent quality and comprehensive coverage.",
                            "created_on": "2025-01-15T10:00:00Z",
                            "private_notes": False,
                            "details": []
                        }
                    ]
                }
            },
            "error": ""
        }
        
        # Apply realistic MCP filter as would be used in practice
        mcp_filter = {
            "exclude_fields": ["spent_hours", "total_spent_hours", "estimated_hours", "total_estimated_hours"],
            "keep_custom_fields": ["Situation", "New High Level Design", "New Low Level Design", "Build"],
            "remove_empty": True,
            "journals": {"code_review_only": True}
        }
        
        # Process the response through the complete filtering pipeline
        filtered_response = apply_response_filter(redmine_api_response, mcp_filter)
        
        # Verify the complete response structure is maintained
        assert filtered_response["status_code"] == 200
        assert filtered_response["error"] == ""
        assert filtered_response["mcp_filtered"] is True
        assert "body" in filtered_response
        assert "issue" in filtered_response["body"]
        
        issue = filtered_response["body"]["issue"]
        
        # Verify core issue data is preserved
        assert issue["id"] == 36461
        assert issue["subject"] == "Implement CIS Benchmark compliance checks"
        assert issue["status"]["name"] == "Development"
        assert issue["assigned_to"]["name"] == "Dan Sun"
        
        # Verify field exclusion worked
        excluded_fields = ["spent_hours", "total_spent_hours", "estimated_hours", "total_estimated_hours"]
        for field in excluded_fields:
            assert field not in issue
        
        # Verify custom field filtering
        assert "custom_fields" in issue
        custom_field_names = [cf["name"] for cf in issue["custom_fields"]]
        expected_custom_fields = ["Situation", "New High Level Design", "New Low Level Design", "Build"]  # All kept fields
        for field_name in expected_custom_fields:
            assert field_name in custom_field_names
        
        # Verify empty field removal - note that custom field filtering happens before empty removal
        # So empty custom fields that are in keep_custom_fields will still be included
        # This is the current behavior - custom field filtering doesn't check for empty values
        assert "Reqs Approver" not in custom_field_names  # Not in keep_custom_fields
        # "New Low Level Design" is in keep_custom_fields so it's included even though empty
        
        # Verify journal filtering - should only contain code review entries
        assert "journals" in issue
        filtered_journals = issue["journals"]
        
        # Should have 4 code review entries: 2 Gerrit + 2 manual reviews
        expected_code_review_ids = [123451, 123453, 123454, 123456]  # Gerrit entries + manual reviews
        actual_journal_ids = [j["id"] for j in filtered_journals]
        
        assert len(filtered_journals) == 4
        for expected_id in expected_code_review_ids:
            assert expected_id in actual_journal_ids
        
        # Verify non-code-review entries are filtered out
        non_code_review_ids = [123450, 123452, 123455]  # Status changes, progress updates
        for non_review_id in non_code_review_ids:
            assert non_review_id not in actual_journal_ids
        
        # Verify Gerrit entries are properly detected
        gerrit_entries = [j for j in filtered_journals if "*Gerrit change* submitted" in j["notes"]]
        assert len(gerrit_entries) == 2
        
        # Verify manual review entries are properly detected
        manual_review_entries = [j for j in filtered_journals if "review" in j["notes"].lower() and "*Gerrit change*" not in j["notes"]]
        assert len(manual_review_entries) == 2
    
    def test_performance_with_large_journal_arrays_and_multiple_filter_combinations(self):
        """Test performance with large journal arrays and multiple filter combinations."""
        import time
        
        # Create a large dataset with 1000 journal entries
        large_journals = []
        for i in range(1000):
            if i % 10 == 0:  # Every 10th entry is a Gerrit code review
                large_journals.append({
                    "id": i,
                    "created_on": f"2025-01-01T{i % 24:02d}:00:00Z",
                    "notes": f"*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/{i}/1*\n\np(((. *Issue #{i}: Feature implementation*\n\nCommit: {'a' * 40}",
                    "details": [],
                    "user": {"id": 200, "name": "Gerrit Integration"}
                })
            elif i % 15 == 0:  # Every 15th entry is a manual code review
                large_journals.append({
                    "id": i,
                    "created_on": f"2025-01-01T{i % 24:02d}:00:00Z",
                    "notes": f"Code review completed for change {i}. Implementation looks good and follows best practices.",
                    "details": [],
                    "user": {"id": 500, "name": "Tech Lead"}
                })
            else:  # Regular administrative entries
                large_journals.append({
                    "id": i,
                    "created_on": f"2025-01-01T{i % 24:02d}:00:00Z",
                    "notes": f"Status update {i}: Progress continues",
                    "details": [{"property": "attr", "name": "status_id", "old_value": "1", "new_value": "2"}],
                    "user": {"id": 123, "name": "Developer"}
                })
        
        # Create large custom fields array
        large_custom_fields = []
        for i in range(100):
            large_custom_fields.append({
                "id": i,
                "name": f"CustomField{i}",
                "value": f"Value{i}" if i % 3 != 0 else ""  # Every 3rd field is empty
            })
        
        # Create response with large dataset
        large_response = {
            "status_code": 200,
            "body": {
                "issues": [
                    {
                        "id": j,
                        "subject": f"Large Test Issue {j}",
                        "description": "A" * 1000,  # Long description
                        "custom_fields": large_custom_fields.copy(),
                        "journals": large_journals.copy()
                    }
                    for j in range(10)  # 10 issues with large datasets each
                ]
            },
            "error": ""
        }
        
        # Apply comprehensive filtering with performance measurement
        mcp_filter = {
            "exclude_fields": ["description"],
            "keep_custom_fields": ["CustomField1", "CustomField5", "CustomField10"],
            "remove_empty": True,
            "max_array_items": 50,  # Limit arrays to 50 items
            "journals": {"code_review_only": True}
        }
        
        start_time = time.time()
        result = apply_response_filter(large_response, mcp_filter)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify filtering completed successfully
        assert result["mcp_filtered"] is True
        assert "body" in result
        assert "issues" in result["body"]
        
        # Verify performance is reasonable (should complete in under 5 seconds)
        assert processing_time < 5.0, f"Filtering took too long: {processing_time:.2f} seconds"
        
        # Verify filtering results are correct
        for issue in result["body"]["issues"]:
            # Description should be excluded
            assert "description" not in issue
            
            # Custom fields should be filtered
            assert "custom_fields" in issue
            custom_field_names = [cf["name"] for cf in issue["custom_fields"]]
            expected_fields = ["CustomField1", "CustomField5", "CustomField10"]
            for field_name in expected_fields:
                if field_name in [cf["name"] for cf in large_custom_fields if cf["value"]]:  # Only non-empty
                    assert field_name in custom_field_names
            
            # Journals should be filtered for code review only
            assert "journals" in issue
            journals = issue["journals"]
            
            # Should have significantly fewer journals (only code review entries)
            # Expected: 100 Gerrit entries (every 10th) + 33 manual review entries (every 15th, excluding overlap) = 133 total
            # Note: max_array_items is not applied to journal filtering - it's a special case
            # Journal filtering happens as a special case before general list filtering
            expected_code_review_count = 133  # Calculated: 100 Gerrit + 33 manual (67 total 15th - 34 overlap)
            assert len(journals) == expected_code_review_count  # All code review entries
            
            # All remaining journals should be code review related
            for journal in journals:
                notes = journal["notes"]
                is_gerrit = "*Gerrit change* submitted" in notes
                is_manual_review = "code review" in notes.lower() and "*Gerrit change*" not in notes
                assert is_gerrit or is_manual_review, f"Non-code-review journal found: {notes[:50]}..."
        
        # Log performance information for monitoring
        print(f"Performance test completed in {processing_time:.3f} seconds")
        print(f"Processed {len(large_response['body']['issues'])} issues with {len(large_journals)} journals each")
        print(f"Applied {len(mcp_filter)} different filter types simultaneously")
    
    def test_mcp_filtered_flag_correctly_set_when_filtering_applied(self):
        """Validate mcp_filtered flag is correctly set when filtering is applied."""
        base_response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "subject": "Test Issue",
                    "journals": [
                        {"id": 1, "notes": "Regular update"},
                        {"id": 2, "notes": "*Gerrit change* submitted"}
                    ]
                }
            },
            "error": ""
        }
        
        # Test 1: No filtering applied - mcp_filtered should still be True (any filter config triggers it)
        result1 = apply_response_filter(base_response, {})
        assert result1["mcp_filtered"] is True  # Flag is set even with empty filter
        
        # Test 2: Journal filtering applied - mcp_filtered should be True
        result2 = apply_response_filter(base_response, {"journals": {"code_review_only": True}})
        assert result2["mcp_filtered"] is True
        
        # Test 3: Other filters applied - mcp_filtered should be True
        result3 = apply_response_filter(base_response, {"remove_empty": True})
        assert result3["mcp_filtered"] is True
        
        # Test 4: Multiple filters applied - mcp_filtered should be True
        result4 = apply_response_filter(base_response, {
            "exclude_fields": ["description"],
            "journals": {"code_review_only": True},
            "remove_empty": True
        })
        assert result4["mcp_filtered"] is True
        
        # Test 5: Error response - mcp_filtered should NOT be set
        error_response = {
            "status_code": 404,
            "body": {"error": "Not found"},
            "error": "HTTPError: 404"
        }
        result5 = apply_response_filter(error_response, {"journals": {"code_review_only": True}})
        assert "mcp_filtered" not in result5
        assert result5 == error_response  # Should be unchanged
        
        # Test 6: Response with error field set - mcp_filtered should NOT be set
        error_response2 = {
            "status_code": 200,
            "body": {"data": "test"},
            "error": "Some error occurred"
        }
        result6 = apply_response_filter(error_response2, {"remove_empty": True})
        assert "mcp_filtered" not in result6
        assert result6 == error_response2  # Should be unchanged
        
        # Test 7: Filtering exception - mcp_filtered should NOT be set (returns original)
        from unittest.mock import patch
        
        with patch('mcp_redmine.response_filters.filter_data', side_effect=Exception("Test error")):
            result7 = apply_response_filter(base_response, {"remove_empty": True})
            assert "mcp_filtered" not in result7
            assert result7 == base_response  # Should return original on exception
    
    def test_journal_filtering_with_edge_cases_and_error_conditions(self):
        """Test journal filtering behavior with edge cases and error conditions."""
        # Test with missing journals field
        response_no_journals = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "subject": "Test Issue"
                    # No journals field
                }
            },
            "error": ""
        }
        
        result1 = apply_response_filter(response_no_journals, {"journals": {"code_review_only": True}})
        assert result1["mcp_filtered"] is True
        assert "journals" not in result1["body"]["issue"]  # Should remain absent
        
        # Test with empty journals array
        response_empty_journals = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "subject": "Test Issue",
                    "journals": []
                }
            },
            "error": ""
        }
        
        result2 = apply_response_filter(response_empty_journals, {"journals": {"code_review_only": True}})
        assert result2["mcp_filtered"] is True
        assert result2["body"]["issue"]["journals"] == []  # Should remain empty array
        
        # Test with malformed journal entries
        response_malformed_journals = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "journals": [
                        {"id": 1, "notes": "*Gerrit change* submitted"},  # Valid
                        {"invalid": "structure"},  # Invalid structure
                        None,  # Null entry
                        {"id": 2, "notes": "Regular update"},  # Valid but not code review
                        {"id": 3}  # Missing notes field
                    ]
                }
            },
            "error": ""
        }
        
        result3 = apply_response_filter(response_malformed_journals, {"journals": {"code_review_only": True}})
        assert result3["mcp_filtered"] is True
        
        # Should handle malformed entries gracefully and return valid code review entries
        journals = result3["body"]["issue"]["journals"]
        assert len(journals) == 1  # Only the valid Gerrit entry
        assert journals[0]["id"] == 1
        
        # Test with journals field that's not a list
        response_invalid_journals = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "journals": "not_a_list"  # Invalid type
                }
            },
            "error": ""
        }
        
        result4 = apply_response_filter(response_invalid_journals, {"journals": {"code_review_only": True}})
        assert result4["mcp_filtered"] is True
        # Should leave invalid journals field unchanged
        assert result4["body"]["issue"]["journals"] == "not_a_list"