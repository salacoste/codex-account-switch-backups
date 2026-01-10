import keyring
from cryptography.fernet import Fernet
from pathlib import Path
import os
from typing import Optional
from codex_account_manager.core.exceptions import CodexError

SERVICE_NAME = "codex-account-manager"
USERNAME = "master-key"

class EncryptionManager:
    """
    Handles AES-256 encryption/decryption of account data.
    Uses Fernet (symmetric encryption).
    Prioritizes OS Keyring for key storage.
    """
    
    def __init__(self, key_path: Optional[Path] = None, key_bytes: Optional[bytes] = None):
        self.key_path = key_path or Path.home() / ".codex-accounts" / "master.key"
        self._cipher: Optional[Fernet] = None
        
        if key_bytes:
            self._cipher = Fernet(key_bytes)

    def load_key(self) -> None:
        """
        Loads the master key from:
        1. Environment Variable (CI/CD)
        2. OS Keyring (Preferred)
        3. Local File (Fallback/Legacy)
        """
        # 1. Try Environment Variable
        env_key = os.getenv("CODEX_MASTER_KEY")
        if env_key:
            self._cipher = Fernet(env_key.encode())
            return

        # 2. Try Keyring
        try:
            stored_key = keyring.get_password(SERVICE_NAME, USERNAME)
            if stored_key:
                self._cipher = Fernet(stored_key.strip().encode())
                return
        except Exception:
            # Keyring might fail in headless/linux environments without proper backend
            pass

        # 3. Try File
        if self.key_path.exists():
            with open(self.key_path, "rb") as f:
                key = f.read().strip()
                if key:
                    self._cipher = Fernet(key)
                    
                    # Auto-Migrate: If we read from file but Keyring was empty (and working), save it!
                    try:
                        keyring.set_password(SERVICE_NAME, USERNAME, key.decode())
                    except Exception:
                        pass # Fail silently on migration
                    return
        
        # No valid key found

    def ensure_key(self) -> bytes:
        """
        Ensures a key exists. If not, generates and saves it to Keyring and File.
        Returns the key bytes.
        """
        self.load_key()
        if self._cipher:
            # We need to return bytes. Fernet object doesn't expose it easily.
            # We re-fetch from source or file.
            # Just for this method's signature contract:
            # 1. Try ENV (Matches load_key priority)
            env_key = os.getenv("CODEX_MASTER_KEY")
            if env_key:
                return env_key.encode()

            try:
                k = keyring.get_password(SERVICE_NAME, USERNAME)
                if k:
                    return k.encode()
            except Exception:
                pass
            
            if self.key_path.exists():
                 with open(self.key_path, "rb") as f:
                    return f.read().strip()
            

            # If loaded from anywhere else but we can't find source bytes, we are in trouble.
            # But this block is only entered if self._cipher is set.
            # Fallback: Just return dummy or raise?
            # Ideally we shouldn't reach here if _cipher is set but no source found 
            # (unless _cipher set manually in init without bytes saved).
            
        # Generate New
        key = Fernet.generate_key()
        key_str = key.decode()
        
        # 1. Save to Keyring
        try:
            keyring.set_password(SERVICE_NAME, USERNAME, key_str)
        except Exception:
            # Warn?
            pass
            
        # 2. Save to File (Backup)
        # Ensure directory exists
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save strict permissions
        with open(self.key_path, "wb") as f:
            f.write(key)
        os.chmod(self.key_path, 0o600)
        
        self._cipher = Fernet(key)
        return key

    def encrypt(self, data: str) -> bytes:
        """Encrypts a string (JSON) into bytes."""
        if not self._cipher:
            self.ensure_key()
        
        if not self._cipher: # Should be set by ensure_key
             raise CodexError("Encryption key could not be loaded or generated.")

        return self._cipher.encrypt(data.encode('utf-8'))

    def decrypt(self, data: bytes) -> str:
        """Decrypts bytes into a string (JSON)."""
        if not self._cipher:
            self.load_key()
            
        if not self._cipher:
             raise CodexError("No encryption key found. Cannot decrypt data.")

        try:
            return self._cipher.decrypt(data).decode('utf-8')
        except Exception as e:
            raise CodexError("Failed to decrypt data. Invalid key or corrupted file.") from e
