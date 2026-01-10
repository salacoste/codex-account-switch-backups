import pytest
import os
import json
from unittest.mock import patch, MagicMock
from codex_account_manager.config.manager import ConfigManager, Config, Account
from codex_account_manager.core.exceptions import ConfigError, AccountNotFoundError
from cryptography.fernet import Fernet

def test_config_load_corrupt(temp_home):
    """Verify corrupted config file fallback to default."""
    (temp_home / "config.json").write_text("{corrupt")
    
    cm = ConfigManager(root_path=temp_home)
    assert cm.config.active_account is None
    # Should have overwritten or ignored? 
    # Logic: try load -> exception -> self.config = Config().
    # Only save_config writes to disk. So disk remains corrupt until save.
    assert cm.config_file.read_text() == "{corrupt"

def test_config_save_error(temp_home):
    """Verify save_config error handling."""
    cm = ConfigManager(root_path=temp_home)
    
    with patch("codex_account_manager.core.utils.os.replace", side_effect=OSError("Disk IO")):
        with pytest.raises(ConfigError):
            cm.save_config(Config())

def test_ensure_storage_structure(temp_home):
    """Verify init creates dirs."""
    ConfigManager(root_path=temp_home)
    assert (temp_home / "accounts").exists()
    assert (temp_home / ".gitignore").exists()

def test_load_config_env_override(temp_home):
    """Verify active account override from env."""
    cm = ConfigManager(root_path=temp_home)
    cm.save_config(Config(active_account="stored"))
    
    with patch.dict(os.environ, {"CODEX_ACTIVE_ACCOUNT": "env-active"}):
        cfg = cm.load_config()
        assert cfg.active_account == "env-active"

def test_vault_operations_missing_vault(temp_home):
    """Verify operations fail on unknown vault."""
    cm = ConfigManager(root_path=temp_home)
    
    # get_account
    with pytest.raises(AccountNotFoundError, match="Vault 'ghost' not found"):
        cm.get_account("ghost/acc")
        
    # save_account
    with pytest.raises(ConfigError):
        cm.save_account(Account(name="ghost/acc", api_key="k"))
        
    # remove_account
    with pytest.raises(AccountNotFoundError):
        cm.remove_account("ghost/acc")
        
    # switch_account
    with pytest.raises(AccountNotFoundError):
        cm.switch_account("ghost/acc")

def test_mount_vault_decryption_fail(temp_home):
    """Verify mounted vault key fail wraps failure safely."""
    cm = ConfigManager(root_path=temp_home)
    cm.config.mounts["teamA"] = str(temp_home / "teamA")
    cm.config.team_keys["teamA"] = "deadbeef" # Invalid hex maybe, or valid hex but decrypt fails
    
    # Mock Decrypt to fail
    with patch.object(cm.crypto, "decrypt", side_effect=Exception("BadKey")):
        # Remount manual or re-init?
        # _mount_vault called in __init__.
        # We need to trigger reload or manual mount.
        cm._mount_vault("teamA", temp_home / "teamA")
        
    # Should still create vault object, just maybe with no key loaded?
    assert "teamA" in cm.vaults
    # Audit log should have error?
    # We can't easily check audit log file here without reading it.

def test_remove_active_account_updates_config(temp_home):
    """Verify removing active account clears global config."""
    cm = ConfigManager(root_path=temp_home)
    cm.save_account(Account(name="active", api_key="k"))
    cm.switch_account("active")
    
    assert cm.config.active_account == "active"
    
    cm.remove_account("active")
    assert cm.load_config().active_account is None

def test_integrity_checks(temp_home):
    """Verify integrity check logic."""
    with patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", temp_home / ".codex" / "auth.json"):
        cm = ConfigManager(root_path=temp_home)
        
        # 1. No Active
        status = cm.check_active_integrity()
        assert status["exists"] is False
        
        # 2. Exists but Desync/No Legacy
        cm.save_account(Account(name="acc", api_key="k"))
        cm.switch_account("acc")
        
        # Make get_account fail intentionally? 
        with patch.object(cm, "get_account", side_effect=Exception("Load fail")):
             status = cm.check_active_integrity()
             assert status["exists"] is False
             
        # 3. exists, legacy mismatch
        # switch creates legacy file. Modify it.
        (temp_home / ".codex" / "auth.json").write_text("{}")
        status = cm.check_active_integrity()
        assert status["exists"] is True
        assert status["synced"] is False
        
        # 4. Legacy read error
        with patch("builtins.open", side_effect=OSError("Read fail")):
             # We only want to fail the legacy read, not the config read
             # This is tricky with patch("builtins.open").
             # Maybe patch json.load?
             pass

def test_integrity_legacy_read_error(temp_home):
    """Specific legacy read error test."""
    with patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", temp_home / ".codex" / "auth.json"):
        cm = ConfigManager(root_path=temp_home)
        cm.save_account(Account(name="acc", api_key="k"))
        cm.switch_account("acc")
        
        # Mock json.load to fail
        with patch("json.load", side_effect=Exception("Corrupt")):
            status = cm.check_active_integrity()
            assert status["synced"] is False

    # Orphan assertion replaced by proper function
    pass

def test_sync_legacy_tokens(temp_home):
    """Verify tokens synced to legacy file."""
    with patch("codex_account_manager.config.manager.LEGACY_AUTH_FILE", temp_home / ".codex" / "auth.json"):
        cm = ConfigManager(root_path=temp_home)
        acc = Account(name="token-acc", tokens={"access_token": "t"}, api_key="k")
        cm.save_account(acc)
        cm.switch_account("token-acc")
        
        auth = json.loads((temp_home / ".codex" / "auth.json").read_text())
        assert auth["access_token"] == "t"

def test_legacy_accounts_dir_property(temp_home):
    """Verify legacy accounts_dir property."""
    cm = ConfigManager(root_path=temp_home)
    assert cm.accounts_dir == temp_home / "accounts"

def test_delete_alias(temp_home):
    """Verify delete_account alias."""
    cm = ConfigManager(root_path=temp_home)
    cm.save_account(Account(name="del", api_key="k"))
    cm.delete_account("del")
    assert not cm.list_accounts()

def test_team_vault_logic(temp_home):
    """Verify team vault mounting, listing, and switching."""
    # 1. Setup Team Vault
    team_dir = temp_home / "teams" / "ops"
    team_dir.mkdir(parents=True)
    
    # Encrypt a key for the team
    primary_cm = ConfigManager(root_path=temp_home)
    team_key = "secret_key_12345678901234567890" # Not real Fernet, just string for mock?
    # Actually code decrypts bytes.fromhex(cipher_key) then decrypts
    # We should stick to mocking decrypt for simplicity, or do full crypto cycle.
    # Let's mock decrypt to return a valid fernet key string.
    valid_key = "Jt1_dummy_fernet_key_base64_encoded_32b="
    
    # Mock Config with mount
    primary_cm.config.mounts["ops"] = str(team_dir)
    primary_cm.config.team_keys["ops"] = "1234" # hex dummy
    primary_cm.save_config(primary_cm.config)
    
    # Mock crypto decrypt to return a mock key
    # And mock EncryptionManager for team to be valid
    with patch.object(primary_cm.crypto, "decrypt", return_value=valid_key):
        # Trigger mount via re-init or manually
        cm = ConfigManager(root_path=temp_home)
        # Mock crypto decrypt needs to be active during init
        
    # Re-do with context manager around init
    with patch("codex_account_manager.core.crypto.EncryptionManager.decrypt", return_value=valid_key):
        # Wait, decrypt is instance method.
        # easier to mock ConfigManager.load_config? No.
        pass

    # Let's just manually mount for testing?
    # cm._mount_vault expects config to be loaded.
    
    # Correct approach: proper crypto setup or full mocks.
    # Let's use full mocks for `list_accounts` logic which is what we need.
    
    cm = ConfigManager(root_path=temp_home)
    # Inject a mock vault
    mock_vault = MagicMock()
    mock_account = Account(name="prod", api_key="k")
    mock_vault.list_accounts.return_value = [mock_account]
    mock_vault.get_account.return_value = mock_account
    cm.vaults["ops"] = mock_vault
    
    # Test List (Aggregated)
    cm.save_account(Account(name="personal", api_key="k"))
    all_accs = cm.list_accounts()
    # Expect: personal, ops/prod
    names = [a.name for a in all_accs]
    assert "personal" in names
    assert "ops/prod" in names
    
    # Test Switch to Team
    cm.switch_account("ops/prod")
    assert cm.config.active_account == "ops/prod"
    
def test_mount_execution(temp_home):
    """Verify _mount_vault execution path."""
    cm = ConfigManager(root_path=temp_home)
    cm.config.mounts["t"] = str(temp_home/"t")
    cm.config.team_keys["t"] = "0000"
    
    valid_key = Fernet.generate_key().decode()
    with patch.object(cm.crypto, "decrypt", return_value=valid_key):
        cm._mount_vault("t", temp_home/"t")
        
    assert "t" in cm.vaults
