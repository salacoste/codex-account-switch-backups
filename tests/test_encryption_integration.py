import pytest
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account

@pytest.fixture
def clean_env(tmp_path):
    return tmp_path

def test_save_account_encrypts_file(clean_env):
    """Verify that save_account writes auth.enc and it is binary/encrypted."""
    mgr = ConfigManager(clean_env)
    
    acc = Account(name="secret-user", api_key="sk-12345")
    mgr.save_account(acc)
    
    # Check file exists
    account_dir = clean_env / "accounts" / "secret-user"
    enc_file = account_dir / "auth.enc"
    legacy_file = account_dir / "auth.json"
    
    assert enc_file.exists()
    assert not legacy_file.exists()
    
    # Check content is encrypted (not plain JSON)
    content = enc_file.read_bytes()
    assert b"sk-12345" not in content # Should be encrypted
    assert content.startswith(b"gAAAA") # Fernet token header usually

def test_load_encrypted_account(clean_env):
    """Verify loading encrypted account works."""
    mgr = ConfigManager(clean_env)
    acc = Account(name="load-test", api_key="sk-load")
    mgr.save_account(acc)
    
    # Reload
    loaded = mgr.get_account("load-test")
    assert loaded.name == "load-test"
    assert loaded.api_key == "sk-load"

def test_list_mixed_accounts(clean_env):
    """Verify listing works with mixed legacy and encrypted."""
    mgr = ConfigManager(clean_env)
    
    # 1. Create Encrypted
    mgr.save_account(Account(name="encrypted", api_key="sk-enc"))
    
    # 2. manually create Legacy
    legacy_dir = clean_env / "accounts" / "legacy"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "auth.json").write_text(
        Account(name="legacy", api_key="sk-leg").model_dump_json()
    )
    
    # List
    accounts = mgr.list_accounts()
    assert len(accounts) == 2
    names = sorted([a.name for a in accounts])
    assert names == ["encrypted", "legacy"]

def test_migration_on_save(clean_env):
    """Verify legacy file is removed when saving in new format."""
    mgr = ConfigManager(clean_env)
    
    # Setup legacy
    slug = "migrating"
    acc_dir = clean_env / "accounts" / slug
    acc_dir.mkdir(parents=True)
    json_path = acc_dir / "auth.json"
    json_path.write_text(Account(name=slug, api_key="sk-old").model_dump_json())
    
    # Load and Save (should trigger migration)
    acc = mgr.get_account(slug)
    # Modify slightly to force save? saving same obj is fine
    acc.tags = ["migrated"]
    mgr.save_account(acc)
    
    assert (acc_dir / "auth.enc").exists()
    assert not json_path.exists()
