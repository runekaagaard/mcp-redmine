#!/usr/bin/env python3
"""
Simple integration tests for journal filtering.
Tests core integration without external dependencies.
"""

import pytest
# Import moved inside test function to avoid env var requirement during collection


class TestJournalFilteringIntegration:
    """Simple integration tests for journal filtering."""
    
    def test_journal_filtering_integration(self):
        """Test journal filtering through the main server interface."""
        # This would normally make an API call, but we'll mock the response
        # to test the integration without external dependencies
        
        # Mock a realistic response structure
        mock_response_data = {
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
        
        # Test that the filtering integration works
        from mcp_redmine.response_filters import apply_response_filter
        
        mcp_filter = {
            "journals": {
                "code_review_only": True
            }
        }
        
        result = apply_response_filter(mock_response_data, mcp_filter)
        
        assert result["mcp_filtered"] is True
        journals = result["body"]["issue"]["journals"]
        
        # Should only have the 2 code review entries
        assert len(journals) == 2
        assert journals[0]["id"] == 2  # Gerrit entry
        assert journals[1]["id"] == 3  # Manual review entry
    
    def test_combined_filtering_integration(self):
        """Test combined filtering features working together."""
        mock_response = {
            "status_code": 200,
            "body": {
                "issue": {
                    "id": 1,
                    "subject": "Test Issue",
                    "description": "",
                    "custom_fields": [
                        {"id": 1, "name": "Build", "value": "v1.0"},
                        {"id": 2, "name": "Contact", "value": ""}
                    ],
                    "journals": [
                        {"id": 1, "notes": "Regular update", "details": []},
                        {"id": 2, "notes": "*Gerrit change* submitted", "details": []}
                    ]
                }
            },
            "error": ""
        }
        
        from mcp_redmine.response_filters import apply_response_filter
        
        mcp_filter = {
            "remove_empty": True,
            "keep_custom_fields": ["Build"],
            "journals": {"code_review_only": True}
        }
        
        result = apply_response_filter(mock_response, mcp_filter)
        
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


# Optional: Real integration tests that require environment setup
@pytest.mark.integration
@pytest.mark.skipif(
    not pytest.importorskip("os").environ.get("REDMINE_URL") or 
    not pytest.importorskip("os").environ.get("REDMINE_API_KEY"),
    reason="Missing REDMINE_URL or REDMINE_API_KEY environment variables"
)
class TestRealIntegration:
    """Real integration tests - only run when environment is configured."""
    
    def test_real_issue_filtering(self):
        """Test filtering with a real issue (requires environment setup)."""
        from mcp_redmine.server import redmine_request
        
        # Use a small test issue to avoid overwhelming context
        result = redmine_request(
            path="/issues/36393.json",
            params={"include": "journals"},
            mcp_filter={
                "journals": {"code_review_only": True},
                "remove_empty": True
            }
        )
        
        import yaml
        response = yaml.safe_load(result)
        
        assert response["status_code"] == 200
        assert response.get("mcp_filtered") is True
        
        # Should have filtered the response
        if "journals" in response["body"]["issue"]:
            # All remaining journals should be code review related
            for journal in response["body"]["issue"]["journals"]:
                notes = journal.get("notes", "").lower()
                assert any(keyword in notes for keyword in [
                    "gerrit", "commit", "review", "merge", "pull request", "pr"
                ])


if __name__ == "__main__":
    # Run unit tests by default, integration tests only with --integration flag
    import sys
    if "--integration" in sys.argv:
        pytest.main([__file__, "-v", "-m", "integration"])
    else:
        pytest.main([__file__ + "::TestJournalFilteringIntegration", "-v"])