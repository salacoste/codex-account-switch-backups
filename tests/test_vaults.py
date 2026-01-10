import pytest
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account, Config
from unittest.mock import patch, MagicMock
from codex_account_manager.core.vault import Vault
from codex_account_manager.core.crypto import EncryptionManager

def test_personal_vault_default(tmp_path):
    """Verify default behavior is personal vault."""
    mgr = ConfigManager(root_path=tmp_path)
    
    # Save standard account
    acc = Account(name="my-acc", api_key="k")
    mgr.save_account(acc)
    
    # List should show prefixed
    listed = mgr.list_accounts()
    assert len(listed) == 1
    assert listed[0].name == "my-acc"
    
    # Get via namespace
    retrieved = mgr.get_account("personal/my-acc")
    assert retrieved.api_key == "k"
    
    # Get via implicit (fallback logic in _parse? No, we default to personal if no slash)
    retrieved_impl = mgr.get_account("my-acc")
    assert retrieved_impl.api_key == "k"

def test_mount_team_vault(tmp_path):
    """Verify mounting a second vault."""
    mgr = ConfigManager(root_path=tmp_path)
    
    # 1. Create Team Directory manually
    team_dir = tmp_path / "teams" / "ops"
    team_dir.mkdir(parents=True)
    
    # 2. Update Config to mount it
    cfg = Config()
    cfg.mounts = {"ops": str(team_dir)}
    mgr.save_config(cfg)
    
    # Re-init manager to pick up mounts
    mgr = ConfigManager(root_path=tmp_path)
    
    assert "ops" in mgr.vaults
    
    # 3. Save account to team vault
    team_acc = Account(name="ops/prod-key", api_key="sk-ops")
    mgr.save_account(team_acc)
    
    # Verify file created in correct place
    expected_file = team_dir / "accounts" / "prod-key" / "auth.enc"
    assert expected_file.exists()
    
    # 4. List accounts
    all_accs = mgr.list_accounts()
    names = [a.name for a in all_accs]
    assert "ops/prod-key" in names

def test_cross_vault_switching(tmp_path):
    """Verify switching between vaults."""
    mgr = ConfigManager(root_path=tmp_path)
    
    # Personal
    mgr.save_account(Account(name="p1", api_key="k1"))
    
    # Mount Team
    team_dir = tmp_path / "teams" / "t1"
    team_dir.mkdir(parents=True)
    cfg = mgr.load_config()
    cfg.mounts = {"t1": str(team_dir)}
    mgr.save_config(cfg)
    mgr = ConfigManager(root_path=tmp_path)
    
    # Team Acc
    mgr.save_account(Account(name="t1/a1", api_key="k2"))
    
    # Switch to team
    mgr.switch_account("t1/a1")
    
    assert mgr.load_config().active_account == "t1/a1"
    
    # Verify Access (get active)
    # Verify Access (get active)
    active = mgr.get_account("t1/a1")
    assert active.api_key == "k2"


def test_vault_missing_dir(tmp_path):
    """Verify list returns empty if dir missing."""
    # Use real Vault directly
    crypto = EncryptionManager()
    vault = Vault(tmp_path / "custom", crypto, None)
    # Don't create dir (although Vault init calls ensure_storage)
    # So we must remove it manually to test logic inside list_accounts
    import shutil
    shutil.rmtree(vault.accounts_dir)
    
    assert vault.list_accounts() == []

def test_vault_read_error(tmp_path):
    """Verify corrupted files skipped."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="ok", api_key="k"))
    
    # Corrupt one
    bad_dir = tmp_path / "accounts" / "bad"
    bad_dir.mkdir()
    (bad_dir / "auth.enc").write_bytes(b"bad data")
    
    # Also test non-dir ignored
    (tmp_path / "accounts" / "file.txt").write_text("ignore")
    
    listed = mgr.list_accounts()
    assert len(listed) == 1
    assert listed[0].name == "ok"

def test_vault_legacy_support(tmp_path):
    """Verify legacy auth.json loading."""
    mgr = ConfigManager(root_path=tmp_path) 
    
    # Create legacy account manually
    legacy_dir = tmp_path / "accounts" / "legacy"
    legacy_dir.mkdir(parents=True)
    
    acc = Account(name="legacy", api_key="old")
    (legacy_dir / "auth.json").write_text(acc.model_dump_json())
    
    # List
    listed = mgr.list_accounts()
    assert len(listed) == 1
    assert listed[0].name == "legacy"
    
    # Get
    got = mgr.get_account("legacy")
    assert got.api_key == "old"
    
    # Save (should upgrade) -> deletes legacy
    mgr.save_account(got)
    assert not (legacy_dir / "auth.json").exists()
    assert (legacy_dir / "auth.enc").exists()

def test_vault_save_store_error(tmp_path):
    """Verify save errors propagate."""
    mgr = ConfigManager(root_path=tmp_path)
    acc = Account(name="a", api_key="k")
    
    with patch("codex_account_manager.core.vault.atomic_write", side_effect=ValueError("WriteFail")):
        import pytest
        # Actually save_account doesn't catch exception in Vault. 
        # But ConfigManager might caught it? 
        # Vault.save_account doesn't wrap "atomic_write" in try/except.
        # So it raises ValueError.
        
        with pytest.raises(ValueError):
           mgr.save_account(acc)

def test_vault_remove_account(tmp_path):
    """Verify remove_account."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="del", api_key="k"))
    
    # Remove
    mgr.delete_account("del") # alias for vault.remove_account
    
    assert [] == mgr.list_accounts()
    
    # Removing non-exist
    from codex_account_manager.core.exceptions import AccountNotFoundError
    with pytest.raises(AccountNotFoundError):
        mgr.delete_account("del")

def test_vault_get_missing(tmp_path):
    """Verify get_account missing raises error."""
    mgr = ConfigManager(root_path=tmp_path)
    from codex_account_manager.core.exceptions import AccountNotFoundError
    with pytest.raises(AccountNotFoundError):
        mgr.get_account("ghost")

def test_vault_audit_logging(tmp_path):
    """Verify audit usage in vault."""
    # We must inject mock audit
    from codex_account_manager.core.audit import AuditManager
    mock_audit = MagicMock(spec=AuditManager)
    
    mgr = ConfigManager(root_path=tmp_path)
    # Patch the audit manager on the internal vault(s)
    # Default is single vault "personal"
    mgr.vaults["personal"].audit = mock_audit
    
    # Save (modify)
    mgr.save_account(Account(name="audited", api_key="k"))
    mock_audit.log_event.assert_called_with("modify", "audited")
    
    # Access decrypted
    mgr.get_account("audited", decrypted=True)
    # called again with access
    calls = mock_audit.log_event.call_args_list
    # args is tuple ("access", "audited", details_dict) if positional
    # Signature: log_event(event_type, account, details=None, ...)
    # Call used positional check: log_event("access", acc.name, {"decrypted": True})
    args = calls[-1][0] 
    assert args[0] == "access"
    assert args[1] == "audited"
    assert args[2] == {"decrypted": True}
    
    # Remove
    mgr.delete_account("audited")
    mock_audit.log_event.assert_called_with("delete", "audited")

def test_vault_slug_renaming(tmp_path):
    """Verify name sanitization."""
    mgr = ConfigManager(root_path=tmp_path)
    # Name with spaces
    acc = Account(name="My Account!", api_key="k")
    mgr.save_account(acc)
    
    listed = mgr.list_accounts()
    assert listed[0].name == "my-account" # Slugified logic

def test_vault_get_error(tmp_path):
    """Verify get_account raises ConfigError on failure."""
    mgr = ConfigManager(root_path=tmp_path)
    # Create valid account
    mgr.save_account(Account(name="broken", api_key="k"))
    
    # Corrupt it
    acc_file = tmp_path / "accounts" / "broken" / "auth.enc"
    acc_file.write_bytes(b"trash")
    
    from codex_account_manager.core.exceptions import ConfigError
    with pytest.raises(ConfigError):
        mgr.get_account("broken")

def test_vault_get_legacy_audit(tmp_path):
    """Verify legacy access is logged."""
    from codex_account_manager.core.audit import AuditManager
    mock_audit = MagicMock(spec=AuditManager)
    
    mgr = ConfigManager(root_path=tmp_path)
    mgr.vaults["personal"].audit = mock_audit
    
    # Create legacy manually
    legacy_dir = tmp_path / "accounts" / "leg"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "auth.json").write_text(Account(name="leg", api_key="k").model_dump_json())
    
    mgr.get_account("leg", decrypted=True)
    
    args = mock_audit.log_event.call_args[0]
    assert args[0] == "access"
    assert args[2] == {"decrypted": True, "legacy": True}
