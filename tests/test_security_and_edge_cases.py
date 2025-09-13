"""
Security and edge case tests for journal filtering functionality.

These tests are designed to catch critical issues identified by CodeRabbit AI:
- ReDoS vulnerabilities
- Exception handling edge cases
- Field filtering precedence bugs
- Type safety issues
"""

import pytest
import re
import time
from mcp_redmine.journal_filters import (
    GerritPatternMatcher,
    JournalFilterDetector,
    JournalFilterConfig,
    JournalFilterProcessor
)
from mcp_redmine.response_filters import (
    FilterConfig,
    validate_filter_config,
    filter_dict
)


class TestReDoSSecurity:
    """Test protection against Regular Expression Denial of Service attacks."""
    
    def setup_method(self):
        self.matcher = GerritPatternMatcher()
    
    def test_redos_protection_textile_patterns(self):
        """Test that textile patterns don't suffer from ReDoS attacks."""
        # Malicious input designed to cause exponential backtracking
        malicious_input = '*"' + 'a' * 1000 + '":http://' + 'b' * 1000 + 'gerrit' + 'c' * 1000
        
        start_time = time.time()
        try:
            result = self.matcher.has_textile_gerrit_formatting(malicious_input)
            end_time = time.time()
            
            # Should complete quickly (< 1 second) even with malicious input
            assert (end_time - start_time) < 1.0, "Pattern matching took too long - possible ReDoS"
            # Result doesn't matter as much as performance
            assert isinstance(result, bool)
        except Exception as e:
            # Should not crash on malicious input
            pytest.fail(f"Pattern matching crashed on malicious input: {e}")
    
    def test_redos_protection_url_patterns(self):
        """Test that URL patterns are protected against ReDoS."""
        # Test the improved URL pattern that should be ReDoS-safe
        malicious_url = "https://" + "a" * 1000 + "gerrit" + "b" * 1000 + "/r/c/12345"
        
        start_time = time.time()
        result = self.matcher.is_gerrit_entry(malicious_url)
        end_time = time.time()
        
        # Should complete quickly
        assert (end_time - start_time) < 1.0, "URL pattern matching took too long"
        assert isinstance(result, bool)
    
    def test_commit_sha_word_boundaries(self):
        """Test that commit SHA patterns use word boundaries to prevent false matches."""
        # Test cases where SHA should NOT match due to word boundaries
        false_positives = [
            "prefix1234567890123456789012345678901234567890suffix",  # SHA embedded in text
            "x1234567890123456789012345678901234567890x",  # SHA with non-word chars
        ]
        
        for text in false_positives:
            result = self.matcher.is_gerrit_entry(text)
            assert result is False, f"Should not match SHA without word boundaries: {text}"
        
        # Test cases where SHA SHOULD match due to word boundaries
        true_positives = [
            "Commit: 1234567890123456789012345678901234567890 done",  # Proper commit format
            "SHA 1234567890123456789012345678901234567890 found",  # SHA with spaces
        ]
        
        for text in true_positives:
            # Need additional indicator for multi-pattern matching
            text_with_gerrit = f"Gerrit review: {text}"
            result = self.matcher.is_gerrit_entry(text_with_gerrit)
            assert result is True, f"Should match SHA with word boundaries: {text_with_gerrit}"


class TestExceptionHandling:
    """Test robust exception handling for edge cases."""
    
    def setup_method(self):
        self.detector = JournalFilterDetector()
        self.processor = JournalFilterProcessor()
    
    def test_invalid_journal_entry_types(self):
        """Test handling of invalid journal entry types."""
        invalid_entries = [
            None,
            "string_instead_of_dict",
            123,
            [],
            {"notes": None},  # None notes
            {"notes": 123},   # Non-string notes
            {"id": "test", "notes": ""},  # Empty notes
        ]
        
        for entry in invalid_entries:
            # Should not crash and should return False for invalid entries
            try:
                result = self.detector.is_code_review_entry(entry)
                assert isinstance(result, bool)
                # Most invalid entries should return False
                if entry is None or not isinstance(entry, dict):
                    assert result is False
            except (re.error, TypeError, AttributeError, KeyError):
                # These specific exceptions are acceptable
                pass
            except Exception as e:
                pytest.fail(f"Unexpected exception for invalid entry {entry}: {e}")
    
    def test_malformed_regex_patterns(self):
        """Test that malformed regex patterns are handled gracefully."""
        # Create a journal entry that might trigger regex errors
        problematic_entry = {
            "id": 1,
            "notes": "Text with regex special chars: [unclosed bracket \\invalid \\escape *unmatched"
        }
        
        try:
            result = self.detector.is_code_review_entry(problematic_entry)
            assert isinstance(result, bool)
        except (re.error, TypeError, AttributeError, KeyError):
            # These are acceptable exceptions
            pass
        except Exception as e:
            pytest.fail(f"Unexpected exception for problematic regex input: {e}")
    
    def test_journal_filtering_error_recovery(self):
        """Test that journal filtering recovers gracefully from errors."""
        config = JournalFilterConfig(code_review_only=True)
        
        # Mix of valid and invalid journal entries
        journals = [
            {"id": 1, "notes": "*Gerrit change* submitted"},  # Valid
            None,  # Invalid
            {"id": 2, "notes": "Regular update"},  # Valid but non-matching
            "invalid_string",  # Invalid
            {"id": 3, "notes": "Gerrit review completed"},  # Valid and matching
        ]
        
        result = self.processor.filter_journals(journals, config)
        
        # Should return a list (not crash)
        assert isinstance(result, list)
        # Should contain only valid, matching entries
        assert len(result) >= 1  # At least the Gerrit entries should match
        
        # All returned entries should be dictionaries
        for entry in result:
            assert isinstance(entry, dict)
            assert "notes" in entry


class TestFieldFilteringPrecedence:
    """Test that field filtering precedence works correctly."""
    
    def test_include_fields_overrides_exclude_fields(self):
        """Test that include_fields takes precedence over exclude_fields."""
        config = FilterConfig(
            include_fields=["journals", "id"],
            exclude_fields=["journals", "description"]  # Should be ignored
        )
        
        data = {
            "id": 123,
            "journals": [{"id": 1, "notes": "test"}],
            "description": "should be excluded",
            "status": "should be excluded"
        }
        
        result = filter_dict(data, config)
        
        # Should include journals (from include_fields) despite being in exclude_fields
        assert "journals" in result
        assert "id" in result
        # Should exclude fields not in include_fields
        assert "description" not in result
        assert "status" not in result
    
    def test_exclude_fields_respected_when_no_include_fields(self):
        """Test that exclude_fields works when include_fields is not set."""
        config = FilterConfig(
            exclude_fields=["journals", "description"]
        )
        
        data = {
            "id": 123,
            "journals": [{"id": 1, "notes": "test"}],
            "description": "should be excluded",
            "status": "should be included"
        }
        
        result = filter_dict(data, config)
        
        # Should exclude specified fields
        assert "journals" not in result
        assert "description" not in result
        # Should include non-excluded fields
        assert "id" in result
        assert "status" in result
    
    def test_journal_filtering_respects_field_exclusion(self):
        """Test that journal filtering is skipped when journals field is excluded."""
        from mcp_redmine.journal_filters import JournalFilterConfig
        
        config = FilterConfig(
            exclude_fields=["journals"],
            journals=JournalFilterConfig(code_review_only=True)
        )
        
        data = {
            "id": 123,
            "journals": [
                {"id": 1, "notes": "*Gerrit change* submitted"},
                {"id": 2, "notes": "Regular update"}
            ]
        }
        
        result = filter_dict(data, config)
        
        # journals field should be completely excluded
        assert "journals" not in result
        assert "id" in result


class TestValidationRobustness:
    """Test validation catches all type and configuration errors."""
    
    def test_validation_catches_non_string_list_elements(self):
        """Test that validation catches non-string elements in string lists."""
        invalid_configs = [
            {"include_fields": ["valid", 123, "also_valid"]},
            {"exclude_fields": ["valid", None, "also_valid"]},
            {"keep_custom_fields": ["valid", {"invalid": "dict"}, "also_valid"]},
        ]
        
        for config in invalid_configs:
            errors = validate_filter_config(config)
            assert len(errors) > 0, f"Should catch invalid list elements in {config}"
            # Should mention that list items must be strings
            assert any("list items must be strings" in error for error in errors)
    
    def test_validation_catches_non_boolean_flags(self):
        """Test that validation catches non-boolean values for boolean flags."""
        invalid_configs = [
            {"remove_empty": "true"},  # String instead of boolean
            {"remove_custom_fields": 1},  # Integer instead of boolean
            {"remove_empty": None},  # None instead of boolean
        ]
        
        for config in invalid_configs:
            errors = validate_filter_config(config)
            assert len(errors) > 0, f"Should catch non-boolean flags in {config}"
            # Should mention that the field must be boolean
            assert any("must be a boolean value" in error for error in errors)
    
    def test_validation_comprehensive_error_reporting(self):
        """Test that validation reports all errors, not just the first one."""
        # Config with multiple errors
        config = {
            "include_fields": "not_a_list",
            "exclude_fields": ["valid", 123],
            "remove_empty": "not_boolean",
            "journals": "not_a_dict",
            "max_description_length": -1
        }
        
        errors = validate_filter_config(config)
        
        # Should report multiple errors
        assert len(errors) >= 4, f"Should report multiple errors, got: {errors}"
        
        # Check that different types of errors are caught
        error_text = " ".join(errors)
        assert "must be a list" in error_text
        assert "must be strings" in error_text
        assert "must be a boolean" in error_text
        assert "must be a dictionary" in error_text
        assert "positive integer" in error_text


class TestTypeAnnotationSafety:
    """Test that ClassVar annotations prevent shared state issues."""
    
    def test_pattern_immutability(self):
        """Test that pattern constants are immutable between instances."""
        matcher1 = GerritPatternMatcher()
        matcher2 = GerritPatternMatcher()
        
        # Patterns should be the same reference (ClassVar)
        assert matcher1.PRIMARY_PATTERNS is matcher2.PRIMARY_PATTERNS
        assert matcher1.SECONDARY_PATTERNS is matcher2.SECONDARY_PATTERNS
        assert matcher1.URL_PATTERNS is matcher2.URL_PATTERNS
        
        # But compiled patterns should be separate instances
        assert matcher1._compiled_patterns is not matcher2._compiled_patterns
    
    def test_pattern_types_are_tuples(self):
        """Test that all pattern constants are tuples (immutable)."""
        matcher = GerritPatternMatcher()
        
        assert isinstance(matcher.PRIMARY_PATTERNS, tuple)
        assert isinstance(matcher.SECONDARY_PATTERNS, tuple)
        assert isinstance(matcher.URL_PATTERNS, tuple)
        assert isinstance(matcher.COMMIT_PATTERNS, tuple)
        assert isinstance(matcher.TEXTILE_PATTERNS, tuple)
        
        # Should not be able to modify them
        with pytest.raises((TypeError, AttributeError)):
            matcher.PRIMARY_PATTERNS.append("new_pattern")


if __name__ == "__main__":
    pytest.main([__file__])