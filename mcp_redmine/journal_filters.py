"""
Journal filtering functionality for Redmine MCP server.

This module provides filtering capabilities to identify and extract code review-related
journal entries from Redmine issues, specifically focusing on Gerrit integration patterns.
"""

import re
from typing import Any, Dict, List, Optional, ClassVar, Tuple
from dataclasses import dataclass
from mcp.server.fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


@dataclass
class JournalFilterConfig:
    """Configuration for journal filtering options."""
    code_review_only: bool = False  # Filter to show only code review-related entries


class GerritPatternMatcher:
    """
    Pattern matcher for detecting Gerrit-specific code review entries in journal text.
    
    Based on analysis of real Gerrit journal entries, this class identifies the specific
    format used by Gerrit-Redmine integrations.
    """
    
    # Primary patterns - most reliable identifiers
    PRIMARY_PATTERNS: ClassVar[Tuple[str, ...]] = (
        r"\*Gerrit change\* submitted",  # Most reliable identifier
    )
    
    # Secondary patterns - additional Gerrit indicators
    SECONDARY_PATTERNS: ClassVar[Tuple[str, ...]] = (
        r"\*\(Gerrit review\)\*",        # Appears in link text
        r"Gerrit change",                # Fallback pattern
        r"Gerrit review",                # Fallback pattern
    )
    
    # URL patterns for Gerrit change URLs
    URL_PATTERNS: ClassVar[Tuple[str, ...]] = (
        r"https?://[^\s]*gerrit[^\s]*/r/c/\d+(?:/\d+)?",  # Secure Gerrit URL pattern
        r"/r/c/\d+/\d+",                 # Gerrit change/patchset pattern
        r"/r/c/\d+",                     # Gerrit change pattern
    )
    
    # Commit and reference patterns
    COMMIT_PATTERNS: ClassVar[Tuple[str, ...]] = (
        r"Commit:\s*\b[a-f0-9]{40}\b",   # Full commit SHA with word boundaries
        r"Issue\s*#\d+:",                # Issue reference in Gerrit context
        r"\b[a-f0-9]{40}\b",             # Standalone commit SHA with word boundaries
    )
    
    # Textile markup patterns specific to Gerrit entries
    TEXTILE_PATTERNS: ClassVar[Tuple[str, ...]] = (
        r'\*"[^"]*":https?://[^\s]*gerrit[^\s]*',  # Textile link to Gerrit (secure)
        r"p\(\(\(\.\s*\*Issue\s*#\d+:",  # Textile paragraph with issue ref
    )
    
    def __init__(self):
        """Initialize the pattern matcher with compiled regex patterns."""
        self._compiled_patterns = {
            'primary': [re.compile(pattern, re.IGNORECASE) for pattern in self.PRIMARY_PATTERNS],
            'secondary': [re.compile(pattern, re.IGNORECASE) for pattern in self.SECONDARY_PATTERNS],
            'url': [re.compile(pattern, re.IGNORECASE) for pattern in self.URL_PATTERNS],
            'commit': [re.compile(pattern, re.IGNORECASE) for pattern in self.COMMIT_PATTERNS],
            'textile': [re.compile(pattern, re.IGNORECASE) for pattern in self.TEXTILE_PATTERNS],
        }
    
    def is_gerrit_entry(self, text: str) -> bool:
        """
        Determine if a journal entry text contains Gerrit code review information.
        
        Args:
            text: Journal entry text to analyze
            
        Returns:
            True if the text appears to be a Gerrit code review entry
        """
        if not text or not isinstance(text, str):
            return False
        
        # Primary patterns are most reliable - if found, it's definitely Gerrit
        for pattern in self._compiled_patterns['primary']:
            if pattern.search(text):
                return True
        
        # For secondary patterns, require additional confirmation
        secondary_matches = sum(1 for pattern in self._compiled_patterns['secondary'] 
                              if pattern.search(text))
        url_matches = sum(1 for pattern in self._compiled_patterns['url'] 
                         if pattern.search(text))
        commit_matches = sum(1 for pattern in self._compiled_patterns['commit'] 
                           if pattern.search(text))
        textile_matches = sum(1 for pattern in self._compiled_patterns['textile'] 
                            if pattern.search(text))
        
        # Require multiple indicators across distinct groups to reduce false positives
        total_indicators = secondary_matches + url_matches + commit_matches + textile_matches
        present_groups = sum(1 for n in (secondary_matches, url_matches, commit_matches, textile_matches) if n > 0)
        return present_groups >= 2 and total_indicators >= 2
    
    def parse_textile_markup(self, text: str) -> Dict[str, Any]:
        """
        Parse textile markup elements from Gerrit journal entries.
        
        Args:
            text: Text containing textile markup
            
        Returns:
            Dictionary containing parsed textile elements
        """
        if not text or not isinstance(text, str):
            return {}
        
        parsed = {
            'bold_text': [],
            'links': [],
            'paragraphs': [],
            'issue_references': []
        }
        
        # Extract bold text (*text*)
        bold_pattern = re.compile(r'\*([^*]+)\*')
        parsed['bold_text'] = [match.group(1) for match in bold_pattern.finditer(text)]
        
        # Extract textile links ("text":url)
        link_pattern = re.compile(r'"([^"]+)":([^\s*]+)')
        for match in link_pattern.finditer(text):
            parsed['links'].append({
                'text': match.group(1),
                'url': match.group(2)
            })
        
        # Extract paragraph formatting (p(((. text) - using safer pattern to avoid ReDoS
        paragraph_pattern = re.compile(r'p\(\(\(\.\s*([^\n]*(?:\n(?!\n)[^\n]*)*)')
        parsed['paragraphs'] = [match.group(1).strip() for match in paragraph_pattern.finditer(text)]
        
        # Extract issue references (Issue #number: title)
        issue_pattern = re.compile(r'Issue\s*#(\d+):\s*([^*\n]+)')
        for match in issue_pattern.finditer(text):
            parsed['issue_references'].append({
                'number': match.group(1),
                'title': match.group(2).strip()
            })
        
        return parsed
    
    def has_textile_gerrit_formatting(self, text: str) -> bool:
        """
        Check if text has textile formatting specific to Gerrit entries.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text contains Gerrit-specific textile formatting
        """
        if not text or not isinstance(text, str):
            return False
        
        # Check for textile patterns specific to Gerrit
        for pattern in self._compiled_patterns['textile']:
            if pattern.search(text):
                return True
        
        # Parse textile markup and check for Gerrit-specific content
        parsed = self.parse_textile_markup(text)
        
        # Check if links point to Gerrit
        for link in parsed.get('links', []):
            if 'gerrit' in link['url'].lower() or '/r/c/' in link['url']:
                return True
        
        # Check if bold text contains Gerrit keywords
        for bold in parsed.get('bold_text', []):
            if any(keyword in bold.lower() for keyword in ['gerrit', 'change', 'review']):
                return True
        
        return False

    def contains_code_review_patterns(self, text: str) -> bool:
        """
        Check if text contains general code review patterns.
        
        This is a broader check that includes common code review keywords
        beyond just Gerrit-specific patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text contains code review patterns
        """
        if not text or not isinstance(text, str):
            return False
        
        # First check Gerrit-specific patterns
        if self.is_gerrit_entry(text):
            return True
        
        # Check for textile Gerrit formatting
        if self.has_textile_gerrit_formatting(text):
            return True
        
        # General code review keywords (case-insensitive)
        code_review_keywords = [
            r'\breview\b', r'\breviewed\b', r'\breviewing\b',
            r'\bapproved\b', r'\bapprove\b', r'\bapproval\b',
            r'\brejected\b', r'\breject\b', r'\brejection\b',
            r'\bcommit\b', r'\bcommitted\b', r'\bcommits\b',
            r'\bmerge\b', r'\bmerged\b', r'\bmerging\b',
            r'\bpull request\b', r'\bPR\b',
            r'\bcode review\b', r'\bpeer review\b',
        ]
        
        # Check for general code review keywords
        keyword_matches = 0
        for keyword in code_review_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                keyword_matches += 1
        
        # Require multiple keyword matches for general patterns
        return keyword_matches >= 2


class JournalFilterDetector:
    """
    Main detector for identifying code review-related journal entries.
    
    This class coordinates pattern matching and provides the main interface
    for journal filtering functionality.
    """
    
    def __init__(self):
        """Initialize the detector with pattern matchers."""
        self.gerrit_matcher = GerritPatternMatcher()
    
    def is_code_review_entry(self, journal_entry: Dict[str, Any]) -> bool:
        """
        Determine if a journal entry contains code review information.
        
        Checks both notes content and custom field changes for code review patterns.
        
        Args:
            journal_entry: Redmine journal entry dictionary
            
        Returns:
            True if the entry has substantive code review notes content or code review-related field changes
        """
        # Extract text content from journal entry
        notes = journal_entry.get('notes', '')
        
        # Check if notes contain code review patterns
        if notes and isinstance(notes, str) and notes.strip():
            if self.contains_code_review_patterns(notes):
                return True
        
        # Check for code review-related custom field changes
        details = journal_entry.get('details', [])
        if self._has_code_review_details(details):
            return True
        
        return False
    
    def contains_code_review_patterns(self, text: str) -> bool:
        """
        Check if text contains code review patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text contains code review patterns
        """
        return self.gerrit_matcher.contains_code_review_patterns(text)
    
    def _has_code_review_details(self, details: List[Dict[str, Any]]) -> bool:
        """
        Check if journal details contain code review-related field changes.
        
        Args:
            details: List of journal detail entries
            
        Returns:
            True if details contain code review-related changes
        """
        if not details:
            return False
        
        for detail in details:
            if not isinstance(detail, dict):
                continue
            property_name = str(detail.get('property') or '')
            name = str(detail.get('name') or '')
            
            # Check for custom field changes that might be code review related
            if property_name == 'cf':  # Custom field
                # Custom fields with code review-related names
                if any(keyword in name.lower() for keyword in
                       ['review', 'commit', 'merge', 'approval', 'gerrit']):
                    return True
        
        return False


class JournalFilterProcessor:
    """
    Journal filter processor that integrates with the existing MCP pipeline.
    
    This class provides the main interface for processing journal arrays in issue responses
    and applying code review filtering based on configuration.
    """
    
    def __init__(self):
        """Initialize the processor with a journal filter detector."""
        self.detector = JournalFilterDetector()
    
    def filter_journals(self, journals: List[Dict[str, Any]], 
                       config: JournalFilterConfig) -> List[Dict[str, Any]]:
        """
        Process journal arrays in issue responses and apply aggressive filtering.
        
        When code_review_only is enabled, this method:
        1. Only includes entries with substantive notes content that matches code review patterns
        2. Excludes all entries with only details field changes
        3. Automatically strips the details field from all returned entries
        
        Args:
            journals: List of Redmine journal entries
            config: Journal filter configuration
            
        Returns:
            Aggressively filtered list of journal entries with details field removed
        """
        if not config.code_review_only:
            return journals
        
        if not journals:
            return []
        
        filtered_journals = []
        
        for journal in journals:
            try:
                if self._should_include_journal_aggressive(journal):
                    # Strip details field to remove old_value/new_value noise
                    cleaned_journal = self._strip_details_field(journal)
                    filtered_journals.append(cleaned_journal)
            except (re.error, TypeError, AttributeError, KeyError) as e:
                # Log warning for pattern matching errors but continue processing
                # This ensures robustness and prevents filtering failures
                journal_id = journal.get('id', 'unknown') if isinstance(journal, dict) else 'invalid'
                logger.warning(f"Journal filtering error for journal {journal_id}: {e}")
                continue
        
        return filtered_journals
    
    def should_include_journal(self, journal_entry: Dict[str, Any]) -> bool:
        """
        Determine if a journal entry should be included based on the filter configuration.
        
        Args:
            journal_entry: The journal entry to evaluate
            
        Returns:
            bool: True if the journal should be included
        """
        try:
            return self.detector.is_code_review_entry(journal_entry)
        except (re.error, TypeError, AttributeError, KeyError) as e:
            # Log warning for pattern matching errors and exclude the entry to be safe
            journal_id = journal_entry.get('id', 'unknown') if isinstance(journal_entry, dict) else 'invalid'
            logger.warning(f"Pattern matching error for journal {journal_id}: {e}")
            return False
    
    def _should_include_journal_aggressive(self, journal_entry: Dict[str, Any]) -> bool:
        """
        Implement aggressive should_include_journal logic using strict pattern detection.
        
        Only includes entries that have substantive notes content with code review patterns.
        Excludes entries with only details field changes or notes that don't match patterns.
        
        Args:
            journal_entry: Redmine journal entry dictionary
            
        Returns:
            True if the journal entry has substantive code review notes content
        """
        try:
            # Only include entries that have notes content with code review patterns
            notes = journal_entry.get('notes', '')
            
            # Must have notes content to be considered
            if not notes or not isinstance(notes, str) or notes.strip() == '':
                return False
            
            # Notes content must match code review patterns
            return self.detector.contains_code_review_patterns(notes)
        except (re.error, TypeError, AttributeError, KeyError) as e:
            # Log warning for pattern matching errors and exclude the entry to be safe
            journal_id = journal_entry.get('id', 'unknown') if isinstance(journal_entry, dict) else 'invalid'
            logger.warning(f"Pattern matching error for journal {journal_id}: {e}")
            return False
    
    def _strip_details_field(self, journal_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove the details field from a journal entry to eliminate old_value/new_value noise.
        
        Args:
            journal_entry: Original journal entry dictionary
            
        Returns:
            Journal entry with details field removed
        """
        if not isinstance(journal_entry, dict):
            return journal_entry
        
        # Create a copy and remove the details field
        cleaned_entry = journal_entry.copy()
        cleaned_entry.pop('details', None)
        
        return cleaned_entry


def filter_journals_for_code_review(journals: List[Dict[str, Any]], 
                                   config: JournalFilterConfig) -> List[Dict[str, Any]]:
    """
    Filter a list of journal entries to include only code review-related entries.
    
    Uses aggressive filtering when code_review_only is enabled:
    - Only includes entries with substantive notes content
    - Strips details field to remove old_value/new_value noise
    
    Args:
        journals: List of Redmine journal entries
        config: Journal filter configuration
        
    Returns:
        Aggressively filtered list of journal entries
    """
    if not config.code_review_only:
        return journals
    
    if not journals:
        return []
    
    processor = JournalFilterProcessor()
    return processor.filter_journals(journals, config)


def should_include_journal(journal_entry: Dict[str, Any]) -> bool:
    """
    Determine if a single journal entry should be included in filtered results.
    
    Uses aggressive filtering logic - only includes entries with substantive
    notes content that matches code review patterns.
    
    Args:
        journal_entry: Redmine journal entry dictionary
        
    Returns:
        True if the journal entry has substantive code review notes content
    """
    detector = JournalFilterDetector()
    try:
        # Must have notes content to be considered
        notes = journal_entry.get('notes', '')
        if not notes or not isinstance(notes, str) or notes.strip() == '':
            return False
        
        # Notes content must match code review patterns
        return detector.contains_code_review_patterns(notes)
    except (re.error, TypeError, AttributeError, KeyError):
        # On any error, exclude the entry to be safe
        return False