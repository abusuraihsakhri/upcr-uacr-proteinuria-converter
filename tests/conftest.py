"""
Pytest configuration and shared fixtures for upcr-uacr-proteinuria-converter tests.
"""
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set a test audit key if not already configured
if not os.getenv("AUDIT_SECRET_KEY"):
    os.environ["AUDIT_SECRET_KEY"] = "test-audit-key-for-testing-only-do-not-use-in-production"
