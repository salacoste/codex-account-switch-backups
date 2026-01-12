
import json
import pytest
from unittest.mock import patch
from typer.testing import CliRunner
from typer import Typer

# Import the specific module where the app is defined
from codex_account_manager.commands import migrate
from codex_account_manager.config.models import AccountType

runner = CliRunner()

@pytest.fixture
def mock_root_app():
    """Create a root app that mounts the migrate command."""
    root = Typer()
    root.add_typer(migrate.app, name="migrate")
    return root

def test_import_success(tmp_path, mock_root_app):
    """Test successful import of legacy credentials."""
    
    # 1. Setup Mock Legacy File
    legacy_dir = tmp_path / ".codex"
    legacy_dir.mkdir()
    auth_file = legacy_dir / "auth.json"
    
    auth_data = {
        "api_key": "sk-legacy-123",
        "email": "old@example.com",
        "access_token": "ey123",
        "random_field": "preserved"
    }
    auth_file.write_text(json.dumps(auth_data))
    
    # 2. Mock ConfigManager
    with patch("codex_account_manager.commands.migrate.ConfigManager") as MockConfig:
        mgr = MockConfig.return_value
        # Account doesn't exist
        mgr.get_account.side_effect = Exception("Not found") 
        
        # 3. Mock LEGACY_AUTH path in the module
        with patch("codex_account_manager.commands.migrate.LEGACY_AUTH", auth_file):
            # Run command: codex-account migrate import --name my-legacy
            result = runner.invoke(mock_root_app, ["migrate", "import", "--name", "my-legacy"], input="n\n") 
            # Input "n" for "Switch to ... now?" confirmation (optional)
            
            print(result.stdout)
            assert result.exit_code == 0
            assert "Successfully imported 'my-legacy'" in result.stdout
            
            # Verify Save
            mgr.save_account.assert_called_once()
            saved_acc = mgr.save_account.call_args[0][0]
            assert saved_acc.name == "my-legacy"
            assert saved_acc.api_key == "sk-legacy-123"
            assert saved_acc.tokens["access_token"] == "ey123"
            assert saved_acc.tokens["random_field"] == "preserved"
            assert saved_acc.type == AccountType.OAUTH

def test_import_missing_file(mock_root_app, tmp_path):
    """Test error when auth file is missing."""
    missing_path = tmp_path / "missing.json"
    
    with patch("codex_account_manager.commands.migrate.LEGACY_AUTH", missing_path):
        result = runner.invoke(mock_root_app, ["migrate", "import"])
        assert result.exit_code == 1
        assert "Legacy auth file not found" in result.stdout

def test_import_invalid_json(mock_root_app, tmp_path):
    """Test error when JSON is corrupt."""
    f = tmp_path / "bad.json"
    f.write_text("{bad json")
    
    with patch("codex_account_manager.commands.migrate.LEGACY_AUTH", f):
        result = runner.invoke(mock_root_app, ["migrate", "import"])
        assert result.exit_code == 1
        assert "Failed to parse" in result.stdout
