import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account
from codex_account_manager.core.exceptions import CodexError

runner = CliRunner()

def test_switch_account_success(mock_config):
    """Verify switching to an existing account updates config and legacy auth."""
    # Setup: Create an account to switch to
    cm = ConfigManager(root_path=mock_config)
    acc = Account(name="New Active", email="new@test.com", api_key="sk-new")
    cm.save_account(acc)
    
    # We also need to mock LEGACY_AUTH_FILE constant in Manager to avoid touching real home
    # ConfigManager is imported in commands/context.py, so we patch it there OR patch the class attribute?
    # Better: patch 'codex_account_manager.config.manager.LEGACY_AUTH_FILE'
    
    fake_legacy_path = mock_config / "legacy_auth.json"
    
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr:
        # We need a real instance but with patched constants? 
        # Actually simplest is to patch the method behavior or class attribute if possible.
        # But 'switch_account' does the logic.
        
        # Let's rely on 'ConfigManager' being instantiated with mock_config, 
        # BUT we must change where it writes the legacy file.
        # Since LEGACY_AUTH_FILE is a global constant in manager.py, we can patch it.
        
        with patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", new=fake_legacy_path):
            MockMgr.return_value = ConfigManager(root_path=mock_config)
            
            result = runner.invoke(app, ["switch", "New Active"])
            
            combined = f"{result.stdout} {result.stderr or ''}"
            assert result.exit_code == 0
            assert "Switched to account 'New Active'" in combined
            
            # Verify global config updated
            cm = ConfigManager(root_path=mock_config)
            cfg = cm.load_config()
            assert cfg.active_account == "new-active"
            
            # Verify legacy auth file written
            assert fake_legacy_path.exists()
            import json
            with open(fake_legacy_path) as f:
                data = json.load(f)
                assert data["api_key"] == "sk-new"
                assert data["email"] == "new@test.com"

def test_switch_non_existent(mock_config):
    """Verify error when switching to unknown account."""
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["switch", "Ghost"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 1
        assert "not found" in combined

def test_status_command(mock_config):
    """Verify status shows active account."""
    cm = ConfigManager(root_path=mock_config)
    # Set active manually
    cfg = cm.load_config()
    cfg.active_account = "current-active"
    cm.save_config(cfg)
    
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["status"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "current-active" in combined

def test_status_no_active(mock_config):
    """Verify status checks when none active."""
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["status"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0 # Warning isn't an error
        assert "No active account" in combined

def test_status_checks_integrity_broken(mock_config):
    """Verify status warns if active account is missing."""
    cm = ConfigManager(root_path=mock_config)
    # Set active to non-existent
    cfg = cm.load_config()
    cfg.active_account = "ghost"
    cm.save_config(cfg)
    
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["status"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert "Integrity Error" in combined
        assert "not found" in combined

def test_status_checks_integrity_desync(mock_config):
    """Verify status warns if auth file is out of sync."""
    # Setup healthy account
    cm = ConfigManager(root_path=mock_config)
    acc = Account(name="Desync", email="d", api_key="k1")
    cm.save_account(acc)
    
    # Fake legacy file path
    fake_legacy = mock_config / "legacy_auth.json"
    
    # Manually write divergent legacy file
    import json
    with open(fake_legacy, "w") as f:
        json.dump({"api_key": "k2_mismatch", "email": "d"}, f)
        
    cfg = cm.load_config()
    cfg.active_account = "desync"
    cm.save_config(cfg)
    
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr, \
         patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", new=fake_legacy):
        
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["status"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert "out of sync" in combined

def test_status_healthy(mock_config):
    """Verify status reports success when synced."""
    # Setup healthy account
    cm = ConfigManager(root_path=mock_config)
    acc = Account(name="Healthy", email="h", api_key="k_match")
    cm.save_account(acc)
    
    fake_legacy = mock_config / "legacy_auth.json"
    
    # Switch to it using our logic to ensure sync
    # We use a temp Manager for setup
    with patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", new=fake_legacy):
        mgr = ConfigManager(root_path=mock_config)
        mgr.switch_account("Healthy")
    
    # Test status
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr, \
         patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", new=fake_legacy):
        
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["status"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert "synced and ready" in combined


def test_exceptions_coverage():
    """Trigger missing exception lines."""
    from codex_account_manager.core.exceptions import AccountExistsError
    e = AccountExistsError("test")
    assert str(e) == "Account 'test' already exists."
    
    # ConfigError pass class
    from codex_account_manager.core.exceptions import ConfigError
    e = ConfigError("msg")
    assert str(e) == "msg"

def test_status_legacy_missing(mock_config):
    """Verify warning when legacy file is missing."""
    cm = ConfigManager(root_path=mock_config)
    acc = Account(name="LegacyMissing", email="m", api_key="k")
    cm.save_account(acc)
    
    cfg = cm.load_config()
    cfg.active_account = "legacymissing"
    cm.save_config(cfg)
    
    # Do NOT write legacy file
    # Mock LEGACY auth file to be somewhere that definitely doesn't exist
    fake_legacy = mock_config / "non_existent_auth.json"
    
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr, \
         patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", new=fake_legacy):
        
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # Result should show warning because legacy doesn't exist
        # Wait, inside status() command:
        # health = list_integrity, check_integrity
        # status calls check_active_integrity
        # if not health["legacy_exists"]: output.warn(...)
        
        result = runner.invoke(app, ["status"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 0
        assert "Legacy auth file missing" in combined

def test_status_codex_error(mock_config):
    """Verify error handling in status."""
    with patch("codex_account_manager.commands.context.ConfigManager") as MockMgr:
        MockMgr.return_value.load_config.side_effect = CodexError("StatusFail")
        
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "StatusFail" in f"{result.stdout} {result.stderr}"

import subprocess
import sys

def test_main_execution_via_subprocess():
    """Verify full main execution logic via subprocess."""
    # This hits the 'if __name__ == "__main__": main()' line
    cmd = [sys.executable, "-m", "codex_account_manager.main", "--help"]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert "Codex Account Manager" in result.stdout
