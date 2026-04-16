"""
Pytest configuration for ORGON backend tests.
Sets up test environment and fixtures.
"""

import os
import sys
from pathlib import Path
import pytest
from dotenv import load_dotenv

# Add parent directory to sys.path for imports
backend_dir = Path(__file__).resolve().parent.parent
app_dir = backend_dir.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Load .env from project root
load_dotenv(app_dir / '.env')

@pytest.fixture(scope='session')
def test_db_url():
    return os.environ.get('DATABASE_URL', 'postgresql://orgon_user:orgon_dev_password@postgres:5432/orgon_db')
