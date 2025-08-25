#!/usr/bin/env python3
"""
Simple validation script for response filtering functionality.
Follows the project's approach of runtime testing rather than unit tests.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Validate filtering functionality works."""
    print("🧪 Testing MCP Redmine Response Filtering")
    print("=" * 40)
    
    try:
        # Test imports
        from mcp_redmine.response_filters import apply_response_filter
        from mcp_redmine.filter_presets import apply_preset
        print("✓ Filtering modules import successfully")
        
        # Test basic filtering
        response = {
            'status_code': 200,
            'body': {'issues': [{'id': 1, 'subject': 'Test', 'description': None}]},
            'error': ''
        }
        
        filtered = apply_response_filter(response, {'remove_empty': True})
        assert 'mcp_filtered' in filtered
        print("✓ Response filtering works")
        
        # Test presets
        preset = apply_preset('clean')
        assert 'remove_empty' in preset
        print("✓ Filter presets work")
        
        print("\n🎉 All filtering functionality validated!")
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
