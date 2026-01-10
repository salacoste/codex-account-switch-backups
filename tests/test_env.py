from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account, Config
from unittest.mock import patch, MagicMock

runner = CliRunner()

def test_env_add_flow(tmp_path):
    """Verify adding env var behaves correctly."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="sk-test"))
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["env", "add", "TEST_KEY", "test_value"])
        assert result.exit_code == 0
        assert "Set TEST_KEY" in f"{result.stdout} {result.stderr}"
        
    updated = mgr.get_account("test")
    assert updated.env_vars["TEST_KEY"] == "test_value"

def test_env_remove_flow(tmp_path):
    """Verify removing env var."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="sk-test", env_vars={"TO_DELETE": "val"}))
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["env", "remove", "TO_DELETE"])
        assert result.exit_code == 0
        assert "Removed TO_DELETE" in f"{result.stdout} {result.stderr}"
        
    updated = mgr.get_account("test")
    assert "TO_DELETE" not in updated.env_vars

def test_env_list_flow(tmp_path):
    """Verify list command output."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="sk-test", env_vars={"VISIBLE": "value_123456789", "SHORT": "123456", "TINY": "1"}))
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["env", "list"])
        assert result.exit_code == 0
        output = f"{result.stdout} {result.stderr}"
        
        assert "VISIBLE" in output
        assert "valu...6789" in output
        assert "SHORT" in output
        assert "12..." in output # Masking mid length
        assert "TINY" in output
        assert "1" in output # No masking

def test_env_no_active_account(tmp_path):
    """Verify error when no active account."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_config(Config(active_account=None))
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        result = runner.invoke(app, ["env", "add", "K", "V"])
        assert result.exit_code == 1
        assert "No active account selected" in f"{result.stdout} {result.stderr}"

def test_env_load_error(tmp_path):
    """Verify error loading active account."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_config(Config(active_account="ghost"))
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        result = runner.invoke(app, ["env", "list"])
        assert result.exit_code == 1
        assert "Failed to load active account" in f"{result.stdout} {result.stderr}"

def test_env_add_save_error(tmp_path):
    """Verify save fails on add."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="k"))
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        with patch.object(ConfigManager, "save_account", side_effect=Exception("SaveFail")):
            result = runner.invoke(app, ["env", "add", "K", "V"])
            assert result.exit_code == 1
            assert "Failed to save account" in f"{result.stdout} {result.stderr}"

def test_env_remove_not_found(tmp_path):
    """Verify warn on remove missing key."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="k"))
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        result = runner.invoke(app, ["env", "remove", "MISSING"])
        assert result.exit_code == 0
        assert "not found" in f"{result.stdout} {result.stderr}"

def test_env_remove_save_error(tmp_path):
    """Verify save fails on remove."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="k", env_vars={"K": "V"}))
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        with patch.object(ConfigManager, "save_account", side_effect=Exception("SaveFail")):
            result = runner.invoke(app, ["env", "remove", "K"])
            assert result.exit_code == 1
            assert "Failed to save account" in f"{result.stdout} {result.stderr}"

def test_env_list_empty(tmp_path):
    """Verify empty list output."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="k")) # No env vars
    mgr.switch_account("test")
    
    with patch("codex_account_manager.commands.env.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        result = runner.invoke(app, ["env", "list"])
        assert result.exit_code == 0
        assert "No custom environment variables" in f"{result.stdout} {result.stderr}"
