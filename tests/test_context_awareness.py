import os
from unittest.mock import patch
from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account, Config

runner = CliRunner()

def test_local_context_set(tmp_path):
    """Verify context set writes file."""
    # 1. Setup
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="local-acc", api_key="k"))
    
    # 2. Run Set in cwd
    # We need to mock Path.cwd() or run inside tmp_path
    with patch("codex_account_manager.commands.local_context.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        # To simulate cwd, we can change dir or mock Path.cwd
        # changing dir is safer for file ops
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["context", "set", "local-acc"])
            assert result.exit_code == 0
            assert "Linked directory" in f"{result.stdout} {result.stderr}"
            
            # Verify file
            assert (tmp_path / ".codex-context").read_text() == "local-acc"
        finally:
            os.chdir(cwd)

def test_env_override_logic(tmp_path):
    """Verify CODEX_ACTIVE_ACCOUNT overrides config."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="global", api_key="k1"))
    mgr.save_account(Account(name="session", api_key="k2"))
    
    # Set global to 'global'
    cfg = Config(active_account="global")
    mgr.save_config(cfg)
    
    # Verify default load
    assert mgr.load_config().active_account == "global"
    
    # Verify Override
    with patch.dict(os.environ, {"CODEX_ACTIVE_ACCOUNT": "session"}):
        loaded = mgr.load_config()
        assert loaded.active_account == "session"
        
        # Verify get_account works with it
        acc = mgr.get_account(loaded.active_account)
        assert acc.name == "session"

def test_run_command_respects_override(tmp_path):
    """Verify 'run' command uses the overridden account."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="session-acc", api_key="session-key"))
    
    # Global config is None or diff
    cfg = Config(active_account=None)
    mgr.save_config(cfg)
    
    with patch("codex_account_manager.commands.run.ConfigManager") as MockMgr, \
         patch("codex_account_manager.commands.run.subprocess.run") as mock_run, \
         patch.dict(os.environ, {"CODEX_ACTIVE_ACCOUNT": "session-acc"}):
        
        MockMgr.return_value = mgr
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(app, ["run", "echo"])
        if result.exit_code != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}") # OutputManager writes here
            
        assert result.exit_code == 0
        
        # Verify correct key injection
        args, kwargs = mock_run.call_args
        assert kwargs["env"]["CODEX_API_KEY"] == "session-key"

def test_local_context_set_invalid(tmp_path):
    """Verify set fails if account doesn't exist."""
    mgr = ConfigManager(root_path=tmp_path)
    # No accounts saved
    
    with patch("codex_account_manager.commands.local_context.ConfigManager") as MockMgr:
        MockMgr.return_value = mgr
        
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["context", "set", "ghost"])
            combined = f"{result.stdout} {result.stderr or ''}"
            assert result.exit_code == 1
            assert "does not exist" in combined
        finally:
            os.chdir(cwd)

def test_local_context_show(tmp_path):
    """Verify show command output."""
    # 1. Test Missing
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["context", "show"])
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "No local context" in combined
        
        # 2. Test Exists
        (tmp_path / ".codex-context").write_text("my-acc")
        result = runner.invoke(app, ["context", "show"])
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "Local Context" in combined
        assert "my-acc" in combined
    finally:
        os.chdir(cwd)

def test_local_context_clear(tmp_path):
    """Verify clear command."""
    # 1. Test Missing (Warns)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["context", "clear"])
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "No context file found" in combined
        
        # 2. Test Exists -> Remove
        (tmp_path / ".codex-context").write_text("cleanup-me")
        result = runner.invoke(app, ["context", "clear"])
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "Removed local context" in combined
        assert not (tmp_path / ".codex-context").exists()
    finally:
        os.chdir(cwd)

def test_local_context_write_error(tmp_path):
    """Verify specific error handling for disk write failure."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="local-acc", api_key="k"))
    
    with patch("codex_account_manager.commands.local_context.ConfigManager") as MockMgr, \
         patch("pathlib.Path.write_text", side_effect=OSError("Disk full")):
        
        MockMgr.return_value = mgr
        
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["context", "set", "local-acc"])
            combined = f"{result.stdout} {result.stderr or ''}"
            assert result.exit_code == 1
            assert "Failed to write context file" in combined
            assert "Disk full" in combined
        finally:
            os.chdir(cwd)
