import pytest
from codex_account_manager.core.crypto import EncryptionManager
from codex_account_manager.core.exceptions import CodexError
from cryptography.fernet import Fernet
from unittest.mock import patch
import os

@pytest.fixture
def temp_key_path(tmp_path):
    return tmp_path / "master.key"

@pytest.fixture
def mock_keyring():
    with patch("codex_account_manager.core.crypto.keyring") as mock:
        store = {}
        def get_pwd(svc, user):
            return store.get((svc, user))
        def set_pwd(svc, user, pwd):
            store[(svc, user)] = pwd
        def del_pwd(svc, user):
            if (svc, user) in store:
                del store[(svc, user)]
            
        mock.get_password.side_effect = get_pwd
        mock.set_password.side_effect = set_pwd
        mock.delete_password.side_effect = del_pwd
        yield mock

def test_init_with_bytes():
    """Verify init with raw bytes."""
    key = Fernet.generate_key()
    manager = EncryptionManager(key_bytes=key)
    assert manager._cipher is not None
    assert manager.decrypt(manager.encrypt("test")) == "test"

def test_load_from_env():
    """Verify loading from environment variable."""
    key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"CODEX_MASTER_KEY": key}):
        manager = EncryptionManager()
        manager.load_key()
        assert manager._cipher is not None
        assert manager.encrypt("test") # Works

def test_keyring_read_failure(temp_key_path, mock_keyring):
    """Verify fallback if keyring read fails."""
    mock_keyring.get_password.side_effect = Exception("Keyring DB Locked")
    
    # 1. No File -> No Key
    manager = EncryptionManager(key_path=temp_key_path)
    manager.load_key()
    assert manager._cipher is None
    
    # 2. File Exists -> Load from File
    key = Fernet.generate_key()
    temp_key_path.write_bytes(key)
    
    manager.load_key()
    assert manager._cipher is not None
    assert manager.decrypt(manager.encrypt("test")) == "test"

def test_keyring_migration_failure(temp_key_path, mock_keyring):
    """Verify silence if migration to keyring fails."""
    # File exists
    key = Fernet.generate_key()
    temp_key_path.write_bytes(key)
    
    # Keyring write fails
    mock_keyring.set_password.side_effect = Exception("Write Fail")
    
    manager = EncryptionManager(key_path=temp_key_path)
    manager.load_key() # Should succeed despite migration fail
    
    assert manager._cipher is not None

def test_ensure_key_keyring_check_failure(temp_key_path, mock_keyring):
    """Verify ensure_key handles keyring read failure gracefully."""
    # Keyring raises error
    mock_keyring.get_password.side_effect = Exception("Fail")
    
    # File exists
    key = Fernet.generate_key()
    temp_key_path.write_bytes(key)
    
    manager = EncryptionManager(key_path=temp_key_path)
    # verify it returns bytes from file
    k_bytes = manager.ensure_key()
    assert k_bytes == key

def test_ensure_key_write_failure(temp_key_path, mock_keyring):
    """Verify ensure_key handles keyring write failure."""
    mock_keyring.get_password.side_effect = None # Returns None (empty)
    mock_keyring.set_password.side_effect = Exception("No write access")
    
    manager = EncryptionManager(key_path=temp_key_path)
    manager.ensure_key()
    
    # Should have saved to file at least
    assert temp_key_path.exists()
    assert manager._cipher is not None

def test_encrypt_no_key_failure(temp_key_path, mock_keyring):
    """Verify encrypt raises if ensure_key fails to produce key."""
    manager = EncryptionManager(key_path=temp_key_path)
    
    # Mock ensure_key to do nothing/fail?
    # Actually ensure_key generates a key if missing.
    # To hit the raise, we need ensure_key to complete but self._cipher to be None.
    # But ensure_key sets self._cipher.
    # Maybe we mock ensure_key?
    
    with patch.object(manager, "ensure_key"):
        # If ensure_key does nothing
        with pytest.raises(CodexError, match="Encryption key could not be loaded"):
            manager.encrypt("test")

def test_decrypt_lazy_load(temp_key_path, mock_keyring):
    """Verify decrypt attempts to load key if missing."""
    key = Fernet.generate_key().decode()
    mock_keyring.set_password("codex-account-manager", "master-key", key)
    
    manager = EncryptionManager(key_path=temp_key_path)
    # No load called yet
    
    f = Fernet(key.encode())
    token = f.encrypt(b"secret")
    
    assert manager.decrypt(token) == "secret"

def test_decrypt_no_key_found(temp_key_path, mock_keyring):
    """Verify decrypt raises if no key loading works."""
    manager = EncryptionManager(key_path=temp_key_path)
    # Empty keyring, no file
    
    with pytest.raises(CodexError, match="No encryption key found"):
        manager.decrypt(b"token")

def test_decrypt_corrupted_data(temp_key_path, mock_keyring):
    """Verify decrypt handles bad tokens."""
    manager = EncryptionManager(key_path=temp_key_path)
    manager.ensure_key()
    
    with pytest.raises(CodexError, match="Failed to decrypt"):
        manager.decrypt(b"trash")

def test_init_sets_cipher(temp_key_path):
    """Verify simple init."""
    manager = EncryptionManager(key_path=temp_key_path)
    assert manager.key_path == temp_key_path

def test_ensure_key_from_env(temp_key_path, mock_keyring):
    """Verify ensure_key returns bytes if loaded from ENV."""
    key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"CODEX_MASTER_KEY": key}):
        manager = EncryptionManager()
        # Should load from ENV
        k_bytes = manager.ensure_key()
        assert k_bytes == key.encode()

def test_ensure_key_redundant_keyring(temp_key_path, mock_keyring):
    """Verify ensure_key refetches from keyring if already loaded."""
    key = Fernet.generate_key().decode()
    mock_keyring.set_password("codex-account-manager", "master-key", key)
    
    manager = EncryptionManager(key_path=temp_key_path)
    manager.load_key() # Loads from keyring
    
    # Now ensure_key called
    k_bytes = manager.ensure_key()
    assert k_bytes == key.encode()

def test_ensure_key_memory_only(mock_keyring):
    """Verify ensure_key behavior when key is memory-only (init with bytes)."""
    key = Fernet.generate_key()
    manager = EncryptionManager(key_bytes=key)
    
    # ensure_key called. _cipher is set.
    # Checks Env, Keyring, File -> All empty/fail.
    # Falls through to Generate New.
    k_bytes = manager.ensure_key()
    assert k_bytes is not None
    assert len(k_bytes) > 0
