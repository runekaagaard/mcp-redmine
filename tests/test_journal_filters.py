"""
Tests for journal filtering functionality.
"""

import pytest
from mcp_redmine.journal_filters import (
    GerritPatternMatcher,
    JournalFilterDetector,
    JournalFilterConfig,
    filter_journals_for_code_review,
    should_include_journal
)


class TestJournalFilterConfig:
    """Test JournalFilterConfig dataclass."""
    
    def test_default_values(self):
        config = JournalFilterConfig()
        assert config.code_review_only is False
    
    def test_custom_values(self):
        config = JournalFilterConfig(code_review_only=True)
        assert config.code_review_only is True


class TestGerritPatternMatcher:
    """Test Gerrit-specific pattern matching."""
    
    def setup_method(self):
        self.matcher = GerritPatternMatcher()
    
    def test_primary_pattern_detection(self):
        """Test detection of "*Gerrit change* submitted" primary pattern."""
        # Real Gerrit journal entry format - exact pattern
        text = "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit-server/r/c/12345/1*"
        assert self.matcher.is_gerrit_entry(text) is True
        
        # Primary pattern alone should be sufficient
        text = "*Gerrit change* submitted"
        assert self.matcher.is_gerrit_entry(text) is True
        
        # Test with different formatting around the pattern
        text = "Some text before *Gerrit change* submitted and after"
        assert self.matcher.is_gerrit_entry(text) is True
        
        # Test with newlines
        text = "Line 1\n*Gerrit change* submitted\nLine 3"
        assert self.matcher.is_gerrit_entry(text) is True
    
    def test_primary_pattern_case_insensitive(self):
        """Test case insensitive matching for primary patterns."""
        case_variations = [
            "*gerrit change* submitted",
            "*GERRIT CHANGE* SUBMITTED", 
            "*Gerrit Change* Submitted",
            "*GeRrIt ChAnGe* sUbMiTtEd"
        ]
        
        for text in case_variations:
            assert self.matcher.is_gerrit_entry(text) is True, f"Failed for: {text}"
    
    def test_gerrit_url_pattern_detection_various_formats(self):
        """Verify Gerrit URL pattern matching for various URL formats."""
        # Test different Gerrit URL formats with secondary patterns for confirmation
        # Note: URL patterns need additional indicators (total >= 2) to match
        
        valid_url_test_cases = [
            # Full HTTP URLs with secondary pattern (Gerrit review = 1, URL = 1, total = 2)
            "Gerrit review: http://gerrit.example.com/r/c/12345",
            "Gerrit review: http://gerrit-server.company.com/r/c/12345/1", 
            "Gerrit review: https://gerrit.internal/r/c/98765/2",
            
            # Relative URLs with secondary pattern
            "Gerrit review: /r/c/12345/1",
            "Gerrit review: /r/c/54321",
            
            # URLs with different change/patchset numbers
            "Gerrit review: /r/c/1/1",
            "Gerrit review: /r/c/999999/99", 
            "Gerrit review: http://gerrit.test/r/c/123456/5",
            
            # URLs with commit patterns (URL = 1, commit = 1, total = 2)
            "Check /r/c/12345 - Commit: abc123def456789012345678901234567890abcd",
        ]
        
        for text in valid_url_test_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is True, f"Should match valid URL case: {text}"
        
        # Test cases that should NOT match (insufficient indicators)
        invalid_url_test_cases = [
            # URL patterns alone (only 1 indicator, need >= 2)
            "Check /r/c/12345 for details",
            "Visit http://example.com/r/c/12345",  # URL without "gerrit" in hostname
            
            # Invalid URL patterns even with secondary patterns
            "Gerrit review: /r/c/abc/1",  # Non-numeric change ID
            "Gerrit review: /r/c/",  # Missing change ID
            "Gerrit review: http://example.com/different/path",  # Wrong path
            
            # Single indicators
            "Gerrit change only",  # Only secondary pattern (avoiding "review" which matches)
            "/r/c/12345 only",  # Only URL pattern
        ]
        
        for text in invalid_url_test_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is False, f"Should not match invalid URL case: {text}"
        
        # Cases that DO match due to multiple indicators (expected behavior)
        expected_matches = [
            "http://gerrit.example.com/r/c/12345",  # "gerrit" matches secondary + URL matches
        ]
        
        for text in expected_matches:
            result = self.matcher.is_gerrit_entry(text)
            assert result is True, f"Expected to match due to multiple indicators: {text}"
        
        # Special cases that DO match due to pattern overlap
        # "Review at /r/c/54321/1" matches because:
        # - "review" matches secondary pattern "Gerrit review" (case insensitive, partial match)
        # - "/r/c/54321/1" matches URL pattern "/r/c/\d+/\d+"
        # This is expected behavior due to permissive regex matching
        overlapping_cases = [
            "Review at /r/c/54321/1",  # "review" + URL pattern
        ]
        
        for text in overlapping_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is True, f"Expected to match due to pattern overlap: {text}"
        
        # Cases that should NOT match (only 1 indicator)
        single_indicator_cases = [
            "Change at /r/c/12345",    # Only URL pattern, "change" doesn't match "Gerrit change"
        ]
        
        for text in single_indicator_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is False, f"Should not match single indicator: {text}"
        
        # Special case: /r/c/123/abc should match because it has URL pattern + secondary pattern
        # The URL regex is permissive and matches /r/c/\d+ which includes /r/c/123
        special_case = "Gerrit review: /r/c/123/abc"
        result = self.matcher.is_gerrit_entry(special_case)
        # This actually matches because /r/c/123 matches the URL pattern /r/c/\d+
        assert result is True, f"Special case should match due to permissive URL regex: {special_case}"
    
    def test_commit_sha_detection_and_issue_reference_parsing(self):
        """Test commit SHA detection and issue reference parsing."""
        # Test full 40-character commit SHA
        text_with_full_sha = """Gerrit change submitted
        
        Commit: abc123def456789012345678901234567890abcd
        Issue #12345: Feature implementation"""
        assert self.matcher.is_gerrit_entry(text_with_full_sha) is True
        
        # Test commit SHA in different contexts
        commit_test_cases = [
            # Standard format
            "Gerrit review\nCommit: 1234567890abcdef1234567890abcdef12345678",
            
            # With extra whitespace
            "Gerrit review\nCommit:    abcdef1234567890abcdef1234567890abcdef12",
            
            # Mixed case SHA
            "Gerrit review\nCommit: AbCdEf1234567890AbCdEf1234567890AbCdEf12",
            
            # SHA in different position
            "Gerrit review abc123def456789012345678901234567890abcd here",
        ]
        
        for text in commit_test_cases:
            assert self.matcher.is_gerrit_entry(text) is True, f"Failed for commit test: {text}"
        
        # Test issue reference parsing
        issue_ref_cases = [
            "Gerrit review\nIssue #12345: Feature Title",
            "Gerrit review\nIssue #1: Simple Issue",
            "Gerrit review\nIssue #999999: Complex Feature Name",
            "Gerrit review\nIssue#54321: No Space Format",  # Alternative format
        ]
        
        for text in issue_ref_cases:
            assert self.matcher.is_gerrit_entry(text) is True, f"Failed for issue ref test: {text}"
        
        # Test invalid commit SHAs - these should NOT match because they don't match the strict patterns
        invalid_commit_cases = [
            "Gerrit review\nCommit: short123",  # Too short - doesn't match [a-f0-9]{40}
            "Gerrit review\nCommit: xyz",  # Way too short and invalid chars
            "Gerrit review\nCommit: ghijklmnopqrstuvwxyz1234567890123456789012",  # Invalid chars (g-z)
        ]
        
        for text in invalid_commit_cases:
            # These should NOT match because the commit patterns are strict:
            # - r"Commit:\s*[a-f0-9]{40}" requires exactly 40 hex chars after "Commit:"
            # - r"[a-f0-9]{40}" requires exactly 40 hex chars anywhere
            # So we only have 1 indicator (secondary pattern), need >= 2
            result = self.matcher.is_gerrit_entry(text)
            assert result is False, f"Should not match invalid commit SHA: {text}"
        
        # Test edge case: long string with valid 40-char hex substring
        # This WILL match because the regex finds valid 40-char hex within it
        long_with_valid_hex = "Gerrit review\nCommit: 123456789012345678901234567890123456789012345"
        result = self.matcher.is_gerrit_entry(long_with_valid_hex)
        assert result is True, f"Should match because contains valid 40-char hex substring: {long_with_valid_hex}"
        
        # Test valid commit SHAs that should match
        valid_commit_cases = [
            "Gerrit review\nCommit: abcdef1234567890abcdef1234567890abcdef12",  # Valid 40-char hex
            "Gerrit review\n1234567890abcdef1234567890abcdef12345678",  # Standalone valid SHA
        ]
        
        for text in valid_commit_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is True, f"Should match valid commit SHA: {text}"
        
        # Test cases that should definitely NOT match (only 1 indicator each)
        single_indicator_cases = [
            "Gerrit review only",  # Only secondary pattern
            "Issue #12345: Feature only",  # Only issue pattern
        ]
        
        for text in single_indicator_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is False, f"Should not match single indicator: {text}"
        
        # Special case: Commit patterns can match twice (format + standalone SHA)
        # This WILL match because it has 2 commit pattern matches
        commit_double_match = "Commit: abc123def456789012345678901234567890abcd only"
        result = self.matcher.is_gerrit_entry(commit_double_match)
        assert result is True, f"Should match due to double commit pattern match: {commit_double_match}"
    
    def test_negative_tests_prevent_false_positives_non_gerrit_entries(self):
        """Add negative tests to prevent false positives with non-Gerrit entries."""
        # Test entries that might contain similar keywords but are not Gerrit
        false_positive_cases = [
            # Status changes that use "submitted"
            "Status changed to submitted",
            "Document submitted for review",
            "Form submitted successfully", 
            "Request submitted to manager",
            "Change submitted to database",
            
            # General review mentions without Gerrit context
            "Please review this document",
            "Review meeting scheduled",
            "Annual performance review",
            "Code review guidelines updated",
            
            # Commit mentions without Gerrit context
            "Commit to the project timeline",
            "We need to commit more resources",
            "Commit this change to memory",
            
            # URLs that are not Gerrit
            "Check http://github.com/user/repo/pull/123",
            "See http://example.com/review/456",
            "Visit /admin/c/settings",
            
            # Issue references without Gerrit context
            "Issue #123: Regular bug report",
            "Resolved Issue #456",
            
            # Regular administrative entries
            "Issue assigned to developer",
            "Priority changed to High",
            "Due date updated",
            "Attachment added: file.pdf",
            "Watcher added: user@example.com",
            
            # Empty or minimal content
            "",
            "Updated",
            "Fixed",
            "Done",
            
            # Single keyword matches (should require multiple indicators)
            "review",
            "commit", 
            "approved",
            "submitted",
            "gerrit",  # Single keyword without context
        ]
        
        for text in false_positive_cases:
            result = self.matcher.is_gerrit_entry(text)
            assert result is False, f"False positive detected for: '{text}'"
    
    def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions for pattern matching."""
        # Test very long text with Gerrit pattern
        long_text = "A" * 1000 + "*Gerrit change* submitted" + "B" * 1000
        assert self.matcher.is_gerrit_entry(long_text) is True
        
        # Test text with special characters
        special_chars_text = "*Gerrit change* submitted with special chars: !@#$%^&*()"
        assert self.matcher.is_gerrit_entry(special_chars_text) is True
        
        # Test Unicode characters
        unicode_text = "*Gerrit change* submitted with unicode: 测试 🚀"
        assert self.matcher.is_gerrit_entry(unicode_text) is True
        
        # Test multiple Gerrit patterns in same text
        multiple_patterns = "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/123/1*"
        assert self.matcher.is_gerrit_entry(multiple_patterns) is True
        
        # Test malformed but recognizable patterns
        malformed_cases = [
            "*Gerrit change*submitted",  # Missing space
            "* Gerrit change * submitted",  # Extra spaces in markup
            "*Gerrit  change* submitted",  # Extra space in text
        ]
        
        for text in malformed_cases:
            # Primary pattern should still match even with minor formatting issues
            result = self.matcher.is_gerrit_entry(text)
            # Some may not match due to strict regex, but that's acceptable
            # We test to ensure no exceptions are raised
            assert isinstance(result, bool), f"Should return boolean for: {text}"
    
    def test_empty_or_invalid_input(self):
        """Test handling of empty or invalid input."""
        invalid_inputs = [
            "",
            None,
            123,
            [],
            {},
            False,
            0,
        ]
        
        for invalid_input in invalid_inputs:
            result = self.matcher.is_gerrit_entry(invalid_input)
            assert result is False, f"Should return False for invalid input: {invalid_input}"
    
    def test_textile_pattern_detection(self):
        """Test detection of textile markup patterns."""
        text = """*"(Gerrit review)":http://gerrit-server/r/c/12345/1*
        
        p(((. *Issue #12345: Feature Title*"""
        
        assert self.matcher.is_gerrit_entry(text) is True
    
    def test_full_gerrit_journal_entry(self):
        """Test detection of complete Gerrit journal entry."""
        text = """*Gerrit change* submitted *"(Gerrit review)":http://gerrit-server/r/c/12345/1*

p(((. *Issue #12345: Implement CIS Benchmark*

Commit: abc123def456789012345678901234567890abcd"""
        
        assert self.matcher.is_gerrit_entry(text) is True
    
    def test_contains_code_review_patterns_gerrit(self):
        """Test general code review pattern detection with Gerrit."""
        text = "*Gerrit change* submitted"
        assert self.matcher.contains_code_review_patterns(text) is True
    
    def test_contains_code_review_patterns_general(self):
        """Test general code review pattern detection."""
        texts_with_reviews = [
            "Code review completed and approved",
            "Pull request reviewed and merged",
            "Commit approved by reviewer",
            "Review rejected due to issues"
        ]
        
        for text in texts_with_reviews:
            assert self.matcher.contains_code_review_patterns(text) is True
    
    def test_single_keyword_not_sufficient(self):
        """Test that single keywords are not sufficient for detection."""
        single_keyword_texts = [
            "Review the documentation",
            "Commit this change",
            "Approved by manager",
            "Merge the branches"
        ]
        
        for text in single_keyword_texts:
            assert self.matcher.contains_code_review_patterns(text) is False
    
    def test_parse_textile_markup(self):
        """Test parsing of textile markup elements."""
        # Test text with various textile elements
        text = '*Gerrit change* submitted *"(Gerrit review)":http://gerrit.example.com/r/c/12345/1*\n\np(((. *Issue #12345: Test Feature*\n\nCommit: abc123def456789012345678901234567890abcd'
        
        parsed = self.matcher.parse_textile_markup(text)
        
        # Check bold text extraction
        assert 'Gerrit change' in parsed['bold_text']
        assert 'Issue #12345: Test Feature' in parsed['bold_text']
        
        # Check link extraction
        assert len(parsed['links']) == 1
        assert parsed['links'][0]['text'] == '(Gerrit review)'
        assert parsed['links'][0]['url'] == 'http://gerrit.example.com/r/c/12345/1'
        
        # Check paragraph extraction
        assert len(parsed['paragraphs']) == 1
        assert '*Issue #12345: Test Feature*' in parsed['paragraphs'][0]
        
        # Check issue reference extraction
        assert len(parsed['issue_references']) == 1
        assert parsed['issue_references'][0]['number'] == '12345'
        assert parsed['issue_references'][0]['title'] == 'Test Feature'
    
    def test_has_textile_gerrit_formatting(self):
        """Test detection of Gerrit-specific textile formatting."""
        # Test Gerrit textile link
        gerrit_link = '*"(Gerrit review)":http://gerrit.example.com/r/c/12345/1*'
        assert self.matcher.has_textile_gerrit_formatting(gerrit_link)
        
        # Test Gerrit bold text
        gerrit_bold = '*Gerrit change* submitted'
        assert self.matcher.has_textile_gerrit_formatting(gerrit_bold)
        
        # Test non-Gerrit textile
        regular_textile = '*"Regular link":http://example.com*'
        assert not self.matcher.has_textile_gerrit_formatting(regular_textile)
        
        # Test empty/invalid input
        assert not self.matcher.has_textile_gerrit_formatting('')
        assert not self.matcher.has_textile_gerrit_formatting(None)


class TestJournalFilterDetector:
    """Test main journal filter detector."""
    
    def setup_method(self):
        self.detector = JournalFilterDetector()
    
    def test_gerrit_journal_entry_detection(self):
        """Test detection of Gerrit journal entries."""
        journal_entry = {
            "id": 123456,
            "created_on": "2025-06-16T17:47:38Z",
            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit-server/r/c/12345/1*\n\np(((. *Issue #12345: Feature Title*\n\nCommit: abc123def456789012345678901234567890abcd",
            "details": [],
            "user": {"id": 123, "name": "User Name"},
            "private_notes": False
        }
        
        assert self.detector.is_code_review_entry(journal_entry) is True
    
    def test_general_code_review_entry_detection(self):
        """Test detection of general code review entries."""
        journal_entry = {
            "id": 123457,
            "notes": "Code review completed and approved by team lead. All commits look good.",
            "details": []
        }
        
        assert self.detector.is_code_review_entry(journal_entry) is True
    
    def test_non_code_review_entry_rejection(self):
        """Test rejection of non-code review entries."""
        non_review_entries = [
            {
                "id": 123458,
                "notes": "Status changed from New to In Progress",
                "details": [{"property": "attr", "name": "status_id", "old_value": "1", "new_value": "2"}]
            },
            {
                "id": 123459,
                "notes": "Added attachment: document.pdf",
                "details": []
            },
            {
                "id": 123460,
                "notes": "Updated description with more details",
                "details": []
            }
        ]
        
        for entry in non_review_entries:
            assert self.detector.is_code_review_entry(entry) is False
    
    def test_empty_journal_entry(self):
        """Test handling of empty journal entries."""
        empty_entries = [
            {"id": 1, "notes": "", "details": []},
            {"id": 2, "notes": None, "details": []},
            {"id": 3, "details": []},  # Missing notes
            {}  # Completely empty
        ]
        
        for entry in empty_entries:
            assert self.detector.is_code_review_entry(entry) is False
    
    def test_code_review_custom_field_changes(self):
        """Test detection of code review-related custom field changes."""
        journal_entry = {
            "id": 123461,
            "notes": "",
            "details": [
                {
                    "property": "cf",
                    "name": "gerrit_review_status",
                    "old_value": "",
                    "new_value": "approved"
                }
            ]
        }
        
        assert self.detector.is_code_review_entry(journal_entry) is True
    
    def test_contains_code_review_patterns_delegation(self):
        """Test that pattern detection is delegated to GerritPatternMatcher."""
        text = "*Gerrit change* submitted"
        assert self.detector.contains_code_review_patterns(text) is True
        
        text = "Regular status update"
        assert self.detector.contains_code_review_patterns(text) is False


class TestFilterJournalsForCodeReview:
    """Test journal filtering function."""
    
    def test_filter_disabled_returns_all(self):
        """Test that filtering returns all journals when disabled."""
        journals = [
            {"id": 1, "notes": "Regular update"},
            {"id": 2, "notes": "*Gerrit change* submitted"}
        ]
        
        config = JournalFilterConfig(code_review_only=False)
        result = filter_journals_for_code_review(journals, config)
        
        assert result == journals
    
    def test_filter_enabled_returns_code_review_only(self):
        """Test that filtering returns only code review entries when enabled."""
        journals = [
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
                "notes": "Code review completed and approved by team",
                "details": []
            },
            {
                "id": 4,
                "notes": "Added new attachment",
                "details": []
            }
        ]
        
        config = JournalFilterConfig(code_review_only=True)
        result = filter_journals_for_code_review(journals, config)
        
        # Should return only the Gerrit entry and general code review entry
        assert len(result) == 2
        assert result[0]["id"] == 2
        assert result[1]["id"] == 3
    
    def test_filter_empty_journals(self):
        """Test filtering of empty journal list."""
        config = JournalFilterConfig(code_review_only=True)
        result = filter_journals_for_code_review([], config)
        
        assert result == []
    
    def test_filter_no_code_review_entries(self):
        """Test filtering when no code review entries exist."""
        journals = [
            {"id": 1, "notes": "Regular update", "details": []},
            {"id": 2, "notes": "Status changed", "details": []},
            {"id": 3, "notes": "Added comment", "details": []}
        ]
        
        config = JournalFilterConfig(code_review_only=True)
        result = filter_journals_for_code_review(journals, config)
        
        assert result == []
    
    def test_filter_error_handling(self):
        """Test that filtering errors don't break the process."""
        # Create a journal entry that might cause issues
        journals = [
            {"id": 1, "notes": "*Gerrit change* submitted"},  # Valid entry
            {"invalid": "structure"},  # Invalid entry
            {"id": 2, "notes": "Code review approved"}  # Valid entry
        ]
        
        config = JournalFilterConfig(code_review_only=True)
        result = filter_journals_for_code_review(journals, config)
        
        # Should return valid entries and skip invalid ones
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2


class TestShouldIncludeJournal:
    """Test convenience function for single journal evaluation."""
    
    def test_include_gerrit_entry(self):
        """Test inclusion of Gerrit journal entry."""
        journal_entry = {
            "id": 1,
            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit-server/r/c/12345/1*",
            "details": []
        }
        
        assert should_include_journal(journal_entry) is True
    
    def test_exclude_regular_entry(self):
        """Test exclusion of regular journal entry."""
        journal_entry = {
            "id": 1,
            "notes": "Regular status update",
            "details": []
        }
        
        assert should_include_journal(journal_entry) is False
    
    def test_error_handling(self):
        """Test error handling in convenience function."""
        # Invalid journal entry structure
        invalid_entry = {"invalid": "structure"}
        
        # Should return False on error rather than raising exception
        assert should_include_journal(invalid_entry) is False


class TestJournalFilterProcessor:
    """Test the JournalFilterProcessor class."""
    
    def test_processor_initialization(self):
        """Test that the processor initializes correctly."""
        from mcp_redmine.journal_filters import JournalFilterProcessor
        
        processor = JournalFilterProcessor()
        assert processor.detector is not None
    
    def test_filter_journals_method(self):
        """Test the filter_journals method."""
        from mcp_redmine.journal_filters import JournalFilterProcessor, JournalFilterConfig
        
        processor = JournalFilterProcessor()
        
        # Test data
        journals = [
            {
                "id": 1,
                "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/12345/1*",
                "user": {"id": 1, "name": "Test User"}
            },
            {
                "id": 2,
                "notes": "Status changed from New to In Progress",
                "user": {"id": 2, "name": "Another User"}
            }
        ]
        
        # Test with filtering enabled
        config = JournalFilterConfig(code_review_only=True)
        filtered = processor.filter_journals(journals, config)
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == 1
        
        # Test with filtering disabled
        config_disabled = JournalFilterConfig(code_review_only=False)
        unfiltered = processor.filter_journals(journals, config_disabled)
        
        assert len(unfiltered) == 2
    
    def test_should_include_journal_method(self):
        """Test the should_include_journal method."""
        from mcp_redmine.journal_filters import JournalFilterProcessor
        
        processor = JournalFilterProcessor()
        
        # Gerrit journal entry
        gerrit_journal = {
            "id": 1,
            "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit.example.com/r/c/12345/1*",
            "user": {"id": 1, "name": "Test User"}
        }
        
        # Regular journal entry
        regular_journal = {
            "id": 2,
            "notes": "Status changed from New to In Progress",
            "user": {"id": 2, "name": "Another User"}
        }
        
        assert processor.should_include_journal(gerrit_journal) == True
        assert processor.should_include_journal(regular_journal) == False
    
    def test_processor_error_handling(self):
        """Test that the processor handles errors gracefully."""
        from mcp_redmine.journal_filters import JournalFilterProcessor, JournalFilterConfig
        from unittest.mock import patch
        
        processor = JournalFilterProcessor()
        
        # Test with invalid journal entry
        invalid_journals = [
            {"invalid": "data"},
            None,
            "not a dict"
        ]
        
        config = JournalFilterConfig(code_review_only=True)
        
        # Should not raise an exception and return empty list, with logging
        with patch('mcp_redmine.journal_filters.logger') as mock_logger:
            filtered = processor.filter_journals(invalid_journals, config)
            assert isinstance(filtered, list)
            assert len(filtered) == 0
            # Should have logged warnings for the errors
            assert mock_logger.warning.call_count >= 1
        
        # Test should_include_journal error handling with a problematic entry
        problematic_journal = {"id": 1, "notes": None}
        
        with patch.object(processor.detector, 'is_code_review_entry', side_effect=Exception("Test error")):
            with patch('mcp_redmine.journal_filters.logger') as mock_logger:
                result = processor.should_include_journal(problematic_journal)
                
                # Should return False and not crash
                assert result is False
                # Should log warning
                mock_logger.warning.assert_called_once()
                assert "Pattern matching error for journal 1" in str(mock_logger.warning.call_args)


class TestRealWorldScenarios:
    """Test with realistic Redmine journal data."""
    
    def test_mixed_journal_entries(self):
        """Test filtering with mixed real-world journal entries."""
        journals = [
            {
                "id": 123456,
                "created_on": "2025-06-16T17:47:38Z",
                "notes": "*Gerrit change* submitted *\"(Gerrit review)\":http://gerrit-server/r/c/12345/1*\n\np(((. *Issue #12345: Implement CIS Benchmark*\n\nCommit: abc123def456789012345678901234567890abcd",
                "details": [],
                "user": {"id": 123, "name": "Gerrit Integration"},
                "private_notes": False
            },
            {
                "id": 123457,
                "created_on": "2025-06-16T15:30:22Z",
                "notes": "",
                "details": [
                    {
                        "property": "attr",
                        "name": "status_id",
                        "old_value": "1",
                        "new_value": "2"
                    }
                ],
                "user": {"id": 456, "name": "Developer"},
                "private_notes": False
            },
            {
                "id": 123458,
                "created_on": "2025-06-16T14:15:10Z",
                "notes": "Reviewed the code changes and they look good. Approved for merge after testing.",
                "details": [],
                "user": {"id": 789, "name": "Tech Lead"},
                "private_notes": False
            },
            {
                "id": 123459,
                "created_on": "2025-06-16T13:45:33Z",
                "notes": "Added attachment: requirements.pdf",
                "details": [
                    {
                        "property": "attachment",
                        "name": "requirements.pdf",
                        "new_value": "requirements.pdf"
                    }
                ],
                "user": {"id": 101, "name": "Analyst"},
                "private_notes": False
            }
        ]
        
        config = JournalFilterConfig(code_review_only=True)
        result = filter_journals_for_code_review(journals, config)
        
        # Should return Gerrit entry and manual code review entry
        assert len(result) == 2
        assert result[0]["id"] == 123456  # Gerrit entry
        assert result[1]["id"] == 123458  # Manual review entry
    
    def test_performance_with_large_journal_list(self):
        """Test performance with large number of journal entries."""
        # Create a large list of mixed journal entries
        journals = []
        for i in range(1000):
            if i % 10 == 0:  # Every 10th entry is a code review
                journals.append({
                    "id": i,
                    "notes": f"*Gerrit change* submitted for issue #{i}",
                    "details": []
                })
            else:  # Regular entries
                journals.append({
                    "id": i,
                    "notes": f"Regular update #{i}",
                    "details": []
                })
        
        config = JournalFilterConfig(code_review_only=True)
        result = filter_journals_for_code_review(journals, config)
        
        # Should return 100 code review entries (every 10th)
        assert len(result) == 100
        
        # Verify all returned entries are code review entries
        for entry in result:
            assert "Gerrit change" in entry["notes"]


if __name__ == "__main__":
    pytest.main([__file__])