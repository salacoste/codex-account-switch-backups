import pytest
import shutil
import tempfile
from pathlib import Path

@pytest.fixture
def temp_home():
    """Create a temporary home directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_config(temp_home):
    """
    Return a ConfigManager configured to use the temp_home.
    Allows testing without touching ~/.codex-accounts
    """
    # We assume ConfigManager allows overriding the base path, 
    # or we might need to patch pathlib.Path.home if it's hardcoded.
    # For now, just providing the temp path fixture.
    return temp_home
