import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account, Config
import subprocess

runner = CliRunner()

def test_account_env_vars_only():
    """Verify account can exist with only env_vars."""
    acc = Account(
        name="aws-prod", 
        env_vars={"AWS_ACCESS_KEY_ID": "AKIA...", "AWS_SECRET_ACCESS_KEY": "s3cr3t"}
    )
    assert acc.env_vars["AWS_ACCESS_KEY_ID"] == "AKIA..."
    assert acc.api_key is None
    assert acc.tokens is None

def test_run_no_active_account(tmp_path):
    """Verify error when no active account is selected."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_config(Config(active_account=None))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["run", "--", "echo", "test"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 1
        assert "No active account selected" in combined

def test_run_missing_account(tmp_path):
    """Verify error when active account references missing file."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_config(Config(active_account="ghost"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["run", "--", "echo", "test"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 1
        assert "Failed to load active account" in combined

def test_run_no_command(tmp_path):
    """Verify error when no command provided."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="test", api_key="k"))
    mgr.save_config(Config(active_account="test"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["run"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 1
        assert "No command provided" in combined

def test_run_token_injection(tmp_path):
    """Verify injection of access_token."""
    mgr = ConfigManager(root_path=tmp_path)
    acc = Account(name="oauth", tokens={"access_token": "valid-token"})
    mgr.save_account(acc)
    mgr.save_config(Config(active_account="oauth"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr, \
         patch("codex_account_manager.commands.run.subprocess.run") as mock_run:
        
        MockMgr.return_value = mgr
        mock_run.return_value.returncode = 0
        
        runner.invoke(app, ["run", "--", "echo"])
        
        args, kwargs = mock_run.call_args
        assert kwargs["env"]["CODEX_ACCESS_TOKEN"] == "valid-token"

def test_run_file_not_found(tmp_path):
    """Verify handling of missing executable."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="valid", api_key="k"))
    mgr.save_config(Config(active_account="valid"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr, \
         patch("codex_account_manager.commands.run.subprocess.run", side_effect=FileNotFoundError):
        
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["run", "--", "missing_exe"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 127
        assert "Command not found" in combined

def test_run_keyboard_interrupt(tmp_path):
    """Verify handling of user interruption."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="valid", api_key="k"))
    mgr.save_config(Config(active_account="valid"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr, \
         patch("codex_account_manager.commands.run.subprocess.run", side_effect=KeyboardInterrupt):
        
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["run", "--", "sleep"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 130
        assert "Interrupted" in combined

def test_run_generic_exception(tmp_path):
    """Verify handling of generic execution failures."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="valid", api_key="k"))
    mgr.save_config(Config(active_account="valid"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr, \
         patch("codex_account_manager.commands.run.subprocess.run", side_effect=Exception("Boom")):
        
        MockMgr.return_value = mgr
        
        result = runner.invoke(app, ["run", "--", "boom"])
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 1
        assert "Execution failed" in combined

def test_run_env_var_injection(tmp_path):
    """Verify injection of account env vars."""
    mgr = ConfigManager(root_path=tmp_path)
    acc = Account(name="env-acc", env_vars={"CUSTOM_VAR": "custom-val"})
    mgr.save_account(acc)
    mgr.save_config(Config(active_account="env-acc"))
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr, \
         patch("codex_account_manager.commands.run.subprocess.run") as mock_run:
        
        MockMgr.return_value = mgr
        mock_run.return_value.returncode = 0
        
        runner.invoke(app, ["run", "--", "echo"])
        
        args, kwargs = mock_run.call_args
        assert kwargs["env"]["CUSTOM_VAR"] == "custom-val"
