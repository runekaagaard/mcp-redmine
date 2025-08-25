"""
Security tests for ReDoS vulnerability prevention.

This module tests that our regex patterns are safe from Regular Expression
Denial of Service (ReDoS) attacks and perform well with malicious input.
"""

import time
import pytest
from mcp_redmine.journal_filters import GerritPatternMatcher


class TestReDoSSecurity:
    """Test ReDoS vulnerability prevention in regex patterns."""
    
    def test_paragraph_pattern_performance_with_malicious_input(self):
        """Test that paragraph pattern doesn't suffer from catastrophic backtracking."""
        matcher = GerritPatternMatcher()
        
        # Create potentially malicious input that could trigger ReDoS
        # This pattern would cause issues with the old vulnerable regex
        malicious_input = "p(((. " + "a" * 1000 + "\n" + "b" * 1000 + "\n\n"
        
        # Measure parsing time - should complete quickly
        start_time = time.time()
        result = matcher.parse_textile_markup(malicious_input)
        end_time = time.time()
        
        # Should complete in well under 1 second even with large input
        parsing_time = end_time - start_time
        assert parsing_time < 0.1, f"Parsing took too long: {parsing_time:.3f}s"
        
        # Should still parse correctly
        assert isinstance(result, dict)
        assert 'paragraphs' in result
    
    def test_paragraph_pattern_with_nested_structures(self):
        """Test paragraph pattern with complex nested structures."""
        matcher = GerritPatternMatcher()
        
        # Test with nested paragraph-like structures that could confuse regex
        complex_input = """p(((. First paragraph
with multiple lines
and complex content

p(((. Second paragraph
Issue #123: Test issue
with more content

Regular text here"""
        
        start_time = time.time()
        result = matcher.parse_textile_markup(complex_input)
        end_time = time.time()
        
        # Should complete quickly
        parsing_time = end_time - start_time
        assert parsing_time < 0.1, f"Parsing took too long: {parsing_time:.3f}s"
        
        # Should extract paragraphs correctly
        assert len(result['paragraphs']) >= 2
    
    def test_paragraph_pattern_with_edge_cases(self):
        """Test paragraph pattern with various edge cases."""
        matcher = GerritPatternMatcher()
        
        edge_cases = [
            "p(((. ",  # Minimal case
            "p(((.\n",  # Just newline
            "p(((. \n\n",  # Double newline
            "p(((. content\n",  # Single line with newline
            "p(((. " + "x" * 10000,  # Very long single line
            "p(((. line1\nline2\nline3\n\n",  # Multiple lines
        ]
        
        for test_input in edge_cases:
            start_time = time.time()
            result = matcher.parse_textile_markup(test_input)
            end_time = time.time()
            
            # Each case should complete quickly
            parsing_time = end_time - start_time
            assert parsing_time < 0.05, f"Edge case took too long: {parsing_time:.3f}s for input: {test_input[:50]}..."
            
            # Should return valid result
            assert isinstance(result, dict)
            assert 'paragraphs' in result
    
    def test_all_patterns_performance(self):
        """Test that all regex patterns perform well with large input."""
        matcher = GerritPatternMatcher()
        
        # Create large input with various patterns
        large_input = """
        *Gerrit change* submitted for review
        "Link text":http://gerrit.example.com/r/c/12345
        p(((. This is a paragraph with Issue #123: Test issue
        Commit: 1234567890abcdef1234567890abcdef12345678
        *Another bold text* with more content
        """ * 100  # Repeat 100 times
        
        start_time = time.time()
        
        # Test all pattern matching methods
        is_gerrit = matcher.is_gerrit_entry(large_input)
        has_textile = matcher.has_textile_gerrit_formatting(large_input)
        has_patterns = matcher.contains_code_review_patterns(large_input)
        parsed = matcher.parse_textile_markup(large_input)
        
        end_time = time.time()
        
        # All operations should complete quickly even with large input
        total_time = end_time - start_time
        assert total_time < 0.5, f"All pattern matching took too long: {total_time:.3f}s"
        
        # Should still work correctly
        assert isinstance(is_gerrit, bool)
        assert isinstance(has_textile, bool)
        assert isinstance(has_patterns, bool)
        assert isinstance(parsed, dict)