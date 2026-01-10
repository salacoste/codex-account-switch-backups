import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from cryptography.fernet import Fernet
from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
import subprocess
import shutil

runner = CliRunner()

def test_team_join_reserved_name(tmp_path):
    """Verify cannot use 'personal' name."""
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)):
        result = runner.invoke(app, ["team", "join", "personal", "git@url"])
        assert result.exit_code == 1
        assert "Reserved" in f"{result.stdout} {result.stderr}"

def test_team_join_duplicate(tmp_path):
    """Verify duplicate mount check."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.config.mounts["ops"] = "/tmp/ops"
    mgr.save_config(mgr.config)
    
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)):
        result = runner.invoke(app, ["team", "join", "ops", "url"])
        assert result.exit_code == 1
        assert "already mounted" in f"{result.stdout} {result.stderr}"

def test_team_join_empty_key(tmp_path):
    """Verify key requirement."""
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value=""):
         
        result = runner.invoke(app, ["team", "join", "new", "url"])
        assert result.exit_code == 1
        assert "Key is required" in f"{result.stdout} {result.stderr}"

def test_team_join_short_key_warning(tmp_path):
    """Verify short key warning."""
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value="short"), \
         patch("codex_account_manager.commands.team.subprocess.run"):
         
        result = runner.invoke(app, ["team", "join", "new", "url"])
        # Should succeed (warning doesn't stop), assuming git mock fine
        # We need git mock to allow success
        pass 
        # Actually this test might fail if git mock isn't set up to succeed mkdir etc.
        # But we just want to verify warning printed.
        assert "Key seems short" in f"{result.stdout} {result.stderr}"

def test_team_join_dir_exists_cleanup(tmp_path):
    """Verify error if dir exists."""
    mgr = ConfigManager(root_path=tmp_path)
    (mgr.root / "teams" / "exists").mkdir(parents=True)
    
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value="key"):
         
        result = runner.invoke(app, ["team", "join", "exists", "url"])
        assert result.exit_code == 1
        assert "already exists" in f"{result.stdout} {result.stderr}"

def test_team_join_git_failure(tmp_path):
    """Verify git clone failure."""
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value="validkey1234567890123456789012"), \
         patch("codex_account_manager.commands.team.subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
         
        result = runner.invoke(app, ["team", "join", "fail", "url"])
        assert result.exit_code == 1
        assert "Failed to clone" in f"{result.stdout} {result.stderr}"

def test_team_join_no_git(tmp_path):
    """Verify git not found."""
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value="key"), \
         patch("codex_account_manager.commands.team.subprocess.run", side_effect=FileNotFoundError):
         
        result = runner.invoke(app, ["team", "join", "nogit", "url"])
        assert result.exit_code == 1
        assert "git command not found" in f"{result.stdout} {result.stderr}"

def test_team_join_save_error_cleanup(tmp_path):
    """Verify cleanup on save error."""
    # We mock save_config to raise
    
    # We need to allow git clone (mocked) to create dir first to test cleanup
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value="key"), \
         patch("codex_account_manager.commands.team.subprocess.run") as mock_git, \
         patch.object(ConfigManager, "save_config", side_effect=Exception("SaveFail")):
         
        # Simulate git creating dir
        def git_side_effect(*args, **kwargs):
            Path(args[0][3]).mkdir(parents=True)
            return MagicMock(returncode=0)
        mock_git.side_effect = git_side_effect
         
        result = runner.invoke(app, ["team", "join", "cleanup", "url"])
        
        assert result.exit_code == 1
        assert "Failed to save configuration" in f"{result.stdout} {result.stderr}"
        # Verify dir gone
        assert not (tmp_path / ".codex-accounts" / "teams" / "cleanup").exists()

def test_team_join_integration_success(tmp_path):
    """Success path integration."""
    with patch("codex_account_manager.commands.team.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.team.Prompt.ask", return_value=Fernet.generate_key().decode()), \
         patch("codex_account_manager.commands.team.subprocess.run") as mock_git:
         
        ConfigManager(root_path=tmp_path) # Init
        
        def git_side_effect(*args, **kwargs):
            Path(args[0][3]).mkdir(parents=True)
            return MagicMock(returncode=0)
        mock_git.side_effect = git_side_effect
        
        result = runner.invoke(app, ["team", "join", "ops", "url"])
        assert result.exit_code == 0
        assert "Successfully joined" in f"{result.stdout} {result.stderr}"
