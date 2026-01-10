from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
import subprocess

runner = CliRunner()

def test_sync_git_missing(tmp_path):
    """Verify error if git not installed."""
    with patch("codex_account_manager.commands.sync.shutil.which", return_value=None), \
         patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)):
         
        result = runner.invoke(app, ["sync", "init", "url"])
        assert result.exit_code == 1
        assert "Git is not installed" in f"{result.stdout} {result.stderr}"

def test_sync_git_error(tmp_path):
    """Verify git error propagation."""
    with patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.sync.subprocess.run") as mock_run:
         
        err = subprocess.CalledProcessError(1, "git", stderr="Fatal git fail")
        mock_run.side_effect = err
        
        result = runner.invoke(app, ["sync", "init", "url"])
        assert result.exit_code == 1
        assert "Git error: Fatal git fail" in f"{result.stdout} {result.stderr}"

def test_sync_init_existing_repo(tmp_path):
    """Verify repo already exists branch."""
    (tmp_path / ".git").mkdir()
    
    with patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)):
         
         # Mock remote check success (matches) to avoid failure there
         with patch("codex_account_manager.commands.sync.subprocess.run") as mock_run:
             mock_run.return_value.stdout = "url"
             mock_run.return_value.returncode = 0
             
             result = runner.invoke(app, ["sync", "init", "url"])
             assert result.exit_code == 0
             assert "already initialized" in f"{result.stdout} {result.stderr}"

def test_sync_init_remote_management(tmp_path):
    """Verify remote add/update logic."""
    (tmp_path / ".git").mkdir()
    
    with patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.sync.subprocess.run") as mock_run:
         
         # 1. Matches: "url" == "url"
         mock_run.return_value.stdout = "url"
         result = runner.invoke(app, ["sync", "init", "url"])
         assert "Remote 'origin' already matches" in f"{result.stdout} {result.stderr}"
         
         # 2. Mismatch: "old" != "new"
         mock_run.return_value.stdout = "old"
         result = runner.invoke(app, ["sync", "init", "new"])
         assert "Updated remote" in f"{result.stdout} {result.stderr}"
         
         # 3. Missing: Raises CodexError (via CalledProcessError) on get-url
         # Then calls remote add
         mock_run.side_effect = [
             subprocess.CalledProcessError(1, "git", stderr="No such remote"), # get-url fails
             MagicMock(stdout="", returncode=0) # add succeeds
         ]
         result = runner.invoke(app, ["sync", "init", "add"])
         assert "Added remote" in f"{result.stdout} {result.stderr}"

def test_sync_push_flow(tmp_path):
    """Verify push conditions."""
    # 1. No .git error
    with patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)):
        result = runner.invoke(app, ["sync", "push"])
        assert result.exit_code == 1
        assert "Git not initialized" in f"{result.stdout} {result.stderr}"
        
    # 2. Commit and Push
    (tmp_path / ".git").mkdir()
    with patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.subprocess.run") as mock_run:
        
        # Mock status returns content
        # Mock rev-parse returns main
        
        def side_effect(cmd, **kwargs):
            if "status" in cmd:
                return MagicMock(stdout="M file")
            if "rev-parse" in cmd:
                return MagicMock(stdout="main")
            return MagicMock(stdout="")
            
        mock_run.side_effect = side_effect
        
        result = runner.invoke(app, ["sync", "push"])
        assert result.exit_code == 0
        assert "Commited changes" in f"{result.stdout} {result.stderr}"
        assert "Successfully synced" in f"{result.stdout} {result.stderr}"

def test_sync_pull_flow(tmp_path):
    """Verify pull conditions."""
    # 1. No .git error
    with patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)):
        result = runner.invoke(app, ["sync", "pull"])
        assert result.exit_code == 1
        assert "Git not initialized" in f"{result.stdout} {result.stderr}"
        
    (tmp_path / ".git").mkdir()
    
    with patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.subprocess.run") as mock_run:
         
        mock_run.return_value.stdout = "main" # rev-parse
        
        # 2. Normal Pull
        result = runner.invoke(app, ["sync", "pull"])
        assert result.exit_code == 0
        
        # 3. Force Pull
        result = runner.invoke(app, ["sync", "pull", "--force"])
        assert result.exit_code == 0
        assert "Forced reset" in f"{result.stdout} {result.stderr}"
        
        # 4. Failure
        mock_run.side_effect = Exception("Fail")
        result = runner.invoke(app, ["sync", "pull"])
        assert result.exit_code == 1
        assert "Pull failed" in f"{result.stdout} {result.stderr}"

def test_sync_init_fresh(tmp_path):
    """Verify clean init flow."""
    with patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.sync.subprocess.run") as mock_run:
         
         # Mock remote check fails (so we add it)
         mock_run.side_effect = [
             MagicMock(returncode=0), # init
             subprocess.CalledProcessError(1, "git", stderr="No remote"), # get-url fails
             MagicMock(returncode=0) # remote add
         ]
         
         result = runner.invoke(app, ["sync", "init", "url"])
         assert result.exit_code == 0
         assert "Initialized local git repository" in f"{result.stdout} {result.stderr}"

def test_sync_push_exception(tmp_path):
    """Verify push exception handling."""
    (tmp_path / ".git").mkdir()
    
    with patch("codex_account_manager.commands.sync.ConfigManager", side_effect=lambda: ConfigManager(root_path=tmp_path)), \
         patch("codex_account_manager.commands.sync.shutil.which", return_value="/bin/git"), \
         patch("codex_account_manager.commands.sync.subprocess.run", side_effect=Exception("PushFail")):
         
         result = runner.invoke(app, ["sync", "push"])
         assert result.exit_code == 1
         assert "Push failed" in f"{result.stdout} {result.stderr}"
