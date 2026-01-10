from pathlib import Path
from typing import List

from codex_account_manager.config.models import Account
from codex_account_manager.core.utils import atomic_write, slugify
from codex_account_manager.core.crypto import EncryptionManager
from codex_account_manager.core.audit import AuditManager
from codex_account_manager.core.exceptions import AccountNotFoundError, ConfigError

class Vault:
    """
    Manages a single secure folder of accounts.
    Can be the Personal Vault or a Team Vault.
    """
    def __init__(self, root_path: Path, encryption_manager: EncryptionManager, audit_manager: AuditManager):
        self.root = root_path
        self.accounts_dir = self.root / "accounts"
        self.crypto = encryption_manager
        self.audit = audit_manager
        
        self.ensure_storage()

    def ensure_storage(self):
        """Creates directory structure."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.accounts_dir.mkdir(exist_ok=True)
        # We generally expect the key to be handled by the caller (ConfigManager) for Team vaults
        # For Personal, it uses standard path.

    def list_accounts(self) -> List[Account]:
        """Lists all accounts in this vault."""
        accounts = []
        if not self.accounts_dir.exists():
            return []
            
        for account_dir in self.accounts_dir.iterdir():
            if not account_dir.is_dir():
                continue
                
            auth_enc = account_dir / "auth.enc"
            auth_legacy = account_dir / "auth.json"
            
            try:
                if auth_enc.exists():
                    with open(auth_enc, "rb") as f:
                        decrypted_json = self.crypto.decrypt(f.read())
                        accounts.append(Account.model_validate_json(decrypted_json))
                elif auth_legacy.exists():
                    with open(auth_legacy, "r") as f:
                        accounts.append(Account.model_validate_json(f.read()))
            except Exception:
                continue
        
        return sorted(accounts, key=lambda a: a.name)

    def get_account(self, name: str, decrypted: bool = False) -> Account:
        slug = slugify(name)
        # Support slug retrieval even if name passed (e.g. from CLI arg)
        # But wait, accounts are stored by slug folders.
        account_dir = self.accounts_dir / slug
        auth_enc = account_dir / "auth.enc"
        auth_legacy = account_dir / "auth.json"
        
        if not auth_enc.exists() and not auth_legacy.exists():
            raise AccountNotFoundError(name)
            
        try:
            if auth_enc.exists():
                with open(auth_enc, "rb") as f:
                    decrypted_json = self.crypto.decrypt(f.read())
                    acc = Account.model_validate_json(decrypted_json)
                    if decrypted and self.audit: 
                        self.audit.log_event("access", acc.name, {"decrypted": True})
                    return acc
            else:
                with open(auth_legacy, "r") as f:
                    acc = Account.model_validate_json(f.read())
                    if decrypted and self.audit:
                        self.audit.log_event("access", acc.name, {"decrypted": True, "legacy": True})
                    return acc
        except Exception as e:
            raise ConfigError(f"Failed to load account '{name}': {e}")

    def save_account(self, account: Account):
        slug = slugify(account.name)
        if slug != account.name:
            account.name = slug
            
        account_dir = self.accounts_dir / slug
        account_dir.mkdir(exist_ok=True)
        
        auth_enc = account_dir / "auth.enc"
        
        json_data = account.model_dump_json(indent=2)
        encrypted_data = self.crypto.encrypt(json_data)
        
        with atomic_write(auth_enc, mode="wb") as f:
            f.write(encrypted_data)
        
        if self.audit:
            self.audit.log_event("modify", account.name)
            
        # Cleanup legacy
        auth_legacy = account_dir / "auth.json"
        if auth_legacy.exists():
            auth_legacy.unlink()

    def remove_account(self, name: str):
        slug = slugify(name)
        account_dir = self.accounts_dir / slug
        
        if not account_dir.exists():
            raise AccountNotFoundError(name)
            
        # Delete contents
        import shutil
        shutil.rmtree(account_dir)
        
        if self.audit:
            self.audit.log_event("delete", name)
