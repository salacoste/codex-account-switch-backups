from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account
from codex_account_manager.core.exceptions import CodexError
from unittest.mock import patch

runner = CliRunner()

def test_add_command_flags(mock_config):
    """Verify adding account non-interactively via flags."""
    # Patch ConfigManager to use the mock_config path
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        # Configure the mock to return a real ConfigManager pointing to temp dir
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, [
            "add", 
            "Flag Account", 
            "--email", "flag@test.com", 
            "--api-key", "sk-flag"
        ])
        
        # OutputManager writes success/error to STDERR (Rich Console(stderr=True))
        # Click's result.stdout usually captures both if mix_stderr=True (default),
        # BUT Rich might bypass capture if not forced.
        # Let's check both for safety.
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 0
        assert "added successfully" in combined
    
    # Verify persistence
    cm = ConfigManager(root_path=mock_config)
    acc = cm.get_account("Flag Account")
    assert acc.email == "flag@test.com"
    assert acc.api_key == "sk-flag"
    assert acc.name == "flag-account" # Slugified

def test_add_command_interactive(mock_config):
    """Verify interactive wizard."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # Simulate user input: Name -> Email -> API Key -> Tags (default)
        result = runner.invoke(app, ["add"], input="Wizard User\nwiz@test.com\nsk-wiz\n\n")
        
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 0
        assert "Account Name" in combined
        assert "Email" in combined
        assert "API Key" in combined
    
    cm = ConfigManager(root_path=mock_config)
    acc = cm.get_account("Wizard User")
    assert acc.email == "wiz@test.com"
    assert acc.name == "wizard-user"

def test_add_duplicate_prevention(mock_config):
    """Verify duplicate accounts are rejected."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # create first
        runner.invoke(app, ["add", "dup", "--email", "e", "--api-key", "k"])
        
        # create second with same name
        result = runner.invoke(app, ["add", "dup", "--email", "e2", "--api-key", "k2"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        
        assert result.exit_code == 1
        assert "already exists" in combined

def test_add_duplicate_force(mock_config):
    """Verify --force overwrites duplicates."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        runner.invoke(app, ["add", "overwrite", "--email", "old", "--api-key", "oldk"])
        
        result = runner.invoke(app, [
            "add", "overwrite", 
            "--email", "new", 
            "--api-key", "newk",
            "--force"
        ])
        
        assert result.exit_code == 0
    
    cm = ConfigManager(root_path=mock_config)
    acc = cm.get_account("overwrite")
    assert acc.email == "new"

def test_list_empty(mock_config):
    """Verify list command with no accounts."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["list"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "No accounts found" in combined

def test_list_accounts_table(mock_config):
    """Verify rich table output."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="A", email="a", api_key="secret_key"))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["list"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "Codex Accounts" in combined
        assert "a" in combined # Name
        assert "secret_key" not in combined # Secret hidden by default

def test_list_accounts_json(mock_config):
    """Verify JSON output and masking."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="J", email="j", api_key="secret-key"))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # Typer context for json flag is tricky in tests if passing to parent group
        # but our main.py handles it separately. 
        # However, our command is `app.command` at root level, so flags might need to be passed strictly.
        # Wait, in main.py `list` is registered on `app`. 
        # The `--json` flag is on the main callback.
        # `runner.invoke(app, ["list", "--json"])` might fail if --json is not on list command.
        # Main callback adds it to global options. 
        # Correct usage: `codex-account --json list`
        
        result = runner.invoke(app, ["--json", "list"])
        
        assert result.exit_code == 0
        import json
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "j"
        assert data[0]["api_key"] == "********" # Masked

def test_list_accounts_json_secrets(mock_config):
    """Verify JSON output with secrets revealed."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="S", email="s", api_key="visible-key"))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # codex-account --json list --show-secrets
        # Note: --show-secrets is defined on the list command itself.
        result = runner.invoke(app, ["--json", "list", "--show-secrets"])
        
        assert result.exit_code == 0
        import json
        data = json.loads(result.stdout)
        assert data[0]["api_key"] == "visible-key"

def test_remove_interactive_yes(mock_config):
    """Verify interactive removal with confirmation."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="To Delete", email="d", api_key="k"))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # Simulate "y" for confirmation
        # Typer prompt/confirm reads from input stream
        result = runner.invoke(app, ["remove", "To Delete"], input="y\n")
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "removed" in combined

    # Verify gone
    assert not (mock_config / "accounts" / "to-delete" / "auth.json").exists()

def test_remove_interactive_no(mock_config):
    """Verify interactive removal abortion."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="Keep Me", email="k", api_key="k"))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # Simulate "n" for confirmation
        result = runner.invoke(app, ["remove", "Keep Me"], input="n\n")
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "Operation cancelled" in combined

    # Verify still there (check encrypted)
    assert (mock_config / "accounts" / "keep-me" / "auth.enc").exists()

def test_remove_force(mock_config):
    """Verify forced removal skips confirmation."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="Force Del", email="f", api_key="k"))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # No input provided, should not hang if force works
        result = runner.invoke(app, ["remove", "Force Del", "--force"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 0
        assert "removed" in combined

    assert not (mock_config / "accounts" / "force-del" / "auth.json").exists()

def test_remove_non_existent(mock_config):
    """Verify error when removing unknown account."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["remove", "Ghost", "--force"])
        
        combined = f"{result.stdout} {result.stderr or ''}"
        assert result.exit_code == 1
        assert "not found" in combined

def test_remove_active_clears_config(mock_config):
    """Verify removing active account clears global config."""
    cm = ConfigManager(root_path=mock_config)
    acc = Account(name="Active One", email="a", api_key="k")
    cm.save_account(acc)
    
    # Set active
    # We need to manually set it since switch isn't tested here yet, 
    # but Manager.delete checks logic is: load_config -> check -> save.
    cfg = cm.load_config()
    cfg.active_account = "active-one"
    cm.save_config(cfg)
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        runner.invoke(app, ["remove", "Active One", "--force"])
        
    cfg_after = cm.load_config()
    assert cfg_after.active_account is None

def test_init_command(mock_config):
    """Verify init command."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, ["init"])
        
        assert result.exit_code == 0
        assert "Initialized storage" in f"{result.stdout} {result.stderr}"

def test_init_error(mock_config):
    with patch("codex_account_manager.commands.account.ConfigManager", side_effect=CodexError("Init Fail")):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1

def test_add_save_error(mock_config):
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        instance.get_account.return_value = None
        instance.save_account.side_effect = CodexError("Save Fail")
        result = runner.invoke(app, ["add", "fail", "--email", "e", "--api-key", "k"])
        assert result.exit_code == 1

def test_list_load_error(mock_config):
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        instance.list_accounts.side_effect = CodexError("List Fail")
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1

def test_encrypt_all_flow(mock_config):
    """Verify encrypt-all scenarios."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        instance.list_accounts.return_value = []
        # Empty
        result = runner.invoke(app, ["encrypt-all", "--yes"])
        assert result.exit_code == 0
        assert "No accounts" in f"{result.stdout} {result.stderr}"
        
        # Interactive No
        instance.list_accounts.return_value = [Account(name="a", api_key="k")]
        result = runner.invoke(app, ["encrypt-all"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in f"{result.stdout} {result.stderr}"
        
        # Success
        result = runner.invoke(app, ["encrypt-all", "--yes"])
        assert result.exit_code == 0
        assert "Successfully encrypted" in f"{result.stdout} {result.stderr}"
        
        # Partial Fail
        instance.list_accounts.return_value = [Account(name="a", api_key="k"), Account(name="b", api_key="k")]
        instance.save_account.side_effect = [None, Exception("F")]
        result = runner.invoke(app, ["encrypt-all", "--yes"]) # re-invoke
        assert "Failed to encrypt b" in f"{result.stdout} {result.stderr}"

    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value.list_accounts.side_effect = CodexError("Fatal")
        result = runner.invoke(app, ["encrypt-all"])
        assert result.exit_code == 1

def test_add_interactive_tags(mock_config):
    """Verify interactive tags input."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        instance.get_account.return_value = None
        
        # Name -> Email -> Key -> Tags
        result = runner.invoke(app, ["add"], input="TagUser\ne\nk\ntag1, tag2 ,tag3\n")
        assert result.exit_code == 0
        
        saved_acc = instance.save_account.call_args[0][0]
        assert saved_acc.tags == ["tag1", "tag2", "tag3"]

def test_list_filter_tag(mock_config):
    """Verify list --tag filtering."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        a1 = Account(name="apple", api_key="k", tags=["dev"])
        a2 = Account(name="banana", api_key="k", tags=["prod"])
        instance.list_accounts.return_value = [a1, a2]
        instance.load_config.return_value.active_account = "apple"
        
        result = runner.invoke(app, ["list", "--tag", "prod"])
        assert result.exit_code == 0
        combined = f"{result.stdout} {result.stderr}"
        assert "banana" in combined
        assert "apple" not in combined

def test_list_json_masking_tokens(mock_config):
    """Verify JSON masking for tokens."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        acc = Account(name="t", tokens={"access_token": "secret"})
        instance.list_accounts.return_value = [acc]
        
        result = runner.invoke(app, ["--json", "list"])
        import json
        data = json.loads(result.stdout)
        assert data[0]["tokens"]["access_token"] == "********"

def test_list_table_credentials(mock_config):
    """Verify credential display options."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        instance = MockMgr.return_value
        a1 = Account(name="k", api_key="key")
        a2 = Account(name="t", tokens={"access_token": "long_token_value_for_oauth_display"})
        a3 = Account(name="s", tokens={"access_token": "short"})
        a4 = Account(name="e", env_vars={"foo":"bar"}) # Valid account but no credentials (key/token)
        instance.list_accounts.return_value = [a1, a2, a3, a4]
        instance.load_config.return_value.active_account = "k"
        
        result = runner.invoke(app, ["list", "--show-secrets"])
        combined = f"{result.stdout} {result.stderr}"
        
        assert "key" in combined
        assert "long_token" in combined
        assert "(OAuth)" in combined
        assert "short" in combined
        assert "Empty" in combined
        assert "Credential" in combined
