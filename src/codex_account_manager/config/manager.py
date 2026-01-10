import os
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple
from pydantic import ValidationError

from codex_account_manager.config.models import Account, Config
from codex_account_manager.core.utils import atomic_write, slugify
from codex_account_manager.core.exceptions import (
    ConfigError, 
    AccountNotFoundError
)
from codex_account_manager.core.crypto import EncryptionManager
from codex_account_manager.core.audit import AuditManager
from codex_account_manager.core.vault import Vault

DEFAULT_CONFIG_ROOT = Path.home() / ".codex-accounts"
# NOTE: Keep this patchable in tests and runtime-expand "~" so that monkeypatching
# HOME works even if this module was imported before the env var change.
LEGACY_AUTH_FILE = "~/.codex/auth.json"


def _resolve_legacy_auth_file() -> Path:
    legacy_auth_file = LEGACY_AUTH_FILE
    if isinstance(legacy_auth_file, Path):
        return legacy_auth_file
    return Path(os.path.expanduser(str(legacy_auth_file)))


class ConfigManager:
    """
    Manages global configuration and orchestrates multiple Vaults.
    - Primary Vault: User's personal accounts.
    - Team Vaults: Mounted shared repositories.
    """

    def __init__(self, root_path: Path = DEFAULT_CONFIG_ROOT):
        self.root = root_path
        self.config_file = self.root / "config.json"
        
        # 1. Global Services
        self.audit = AuditManager(root_path=self.root)
        self.crypto = EncryptionManager(key_path=self.root / "master.key")
        self.crypto.ensure_key() # Primary Key always needed
        
        self._ensure_storage()
        
        # 2. Load Config
        try:
            self.config = self.load_config()
        except ConfigError:
            self.config = Config() # Start fresh/empty if corrupt
            
        # 3. Initialize Vaults
        self.vaults: Dict[str, Vault] = {}
        
        # Primary Vault (personal)
        self.primary_vault = Vault(self.root, self.crypto, self.audit)
        self.vaults["personal"] = self.primary_vault
        
        # Team Vaults
        for mount_slug, mount_path_str in self.config.mounts.items():
            self._mount_vault(mount_slug, Path(mount_path_str))

    def _get_legacy_auth_file(self) -> Path:
        env_override = os.environ.get("CODEX_LEGACY_AUTH_FILE")
        if env_override:
            return Path(env_override).expanduser()

        # If the caller chose a non-default storage root and didn't override the legacy auth path,
        # keep all side-effects confined to that root (important for tests/sandboxed runs).
        if self.root != DEFAULT_CONFIG_ROOT and str(LEGACY_AUTH_FILE) == "~/.codex/auth.json":
            return self.root / ".codex" / "auth.json"

        return _resolve_legacy_auth_file()

    def _ensure_storage(self):
        """Creates basic directory structure."""
        self.root.mkdir(parents=True, exist_ok=True)
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
             with atomic_write(gitignore) as f:
                f.write("*\n!.gitignore\n")

    def _mount_vault(self, slug: str, path: Path):
        """Initializes a mounted vault."""
        # 1. Retrieve Key
        cipher_key = self.config.team_keys.get(slug)
        key_bytes = None
        
        if cipher_key:
            try:
                # Decrypt team usage key using Primary Master Key
                key_str = self.crypto.decrypt(bytes.fromhex(cipher_key))
                key_bytes = key_str.encode()
            except Exception:
                 # Key fail? Log it but don't crash
                 self.audit.log_event("error", f"system/{slug}", {"msg": "Failed to decrypt team key"})
        
        team_crypto = EncryptionManager(key_path=path / "master.key", key_bytes=key_bytes)
        self.vaults[slug] = Vault(path, team_crypto, self.audit)

    def load_config(self) -> Config:
        if not self.config_file.exists():
            return Config()
        try:
            with open(self.config_file, "r") as f:
                cfg = Config.model_validate_json(f.read())
            
            # Session Override logic
            env_override = os.environ.get("CODEX_ACTIVE_ACCOUNT")
            if env_override:
                cfg.active_account = env_override
            return cfg
        except (json.JSONDecodeError, ValidationError) as e:
            raise ConfigError(f"Global configuration corrupted: {e}")

    def save_config(self, config: Config):
        try:
            with atomic_write(self.config_file) as f:
                f.write(config.model_dump_json(indent=2))
            self.config = config # Update in-memory
        except OSError as e:
            raise ConfigError(f"Failed to save configuration: {e}")

    @property
    def accounts_dir(self) -> Path:
        """Legacy compatibility: returns primary vault accounts dir."""
        return self.primary_vault.root / "accounts"

    # --- Account Operations (Proxied to Vaults) ---

    def _parse_account_ref(self, ref: str) -> Tuple[str, str]:
        """Parses 'vault/account' or 'account'. Returns (vault_slug, account_slug)."""
        if "/" in ref:
            parts = ref.split("/", 1)
            return parts[0], parts[1]
        return "personal", ref

    def list_accounts(self) -> List[Account]:
        """Aggregates accounts from all vaults. Namespaces non-primary ones."""
        all_accounts = []
        
        # Personal (No prefix for backward compatibility)
        for acc in self.primary_vault.list_accounts():
             # Legacy tests expect just "name", not "personal/name"
            all_accounts.append(acc)
            
        # Teams
        for vault_slug, vault in self.vaults.items():
            if vault_slug == "personal":
                continue
            for acc in vault.list_accounts():
                acc_copy = acc.model_copy()
                acc_copy.name = f"{vault_slug}/{acc.name}"
                all_accounts.append(acc_copy)
                
        return sorted(all_accounts, key=lambda a: a.name)

    def get_account(self, name: str, decrypted: bool = False) -> Account:
        vault_slug, acc_slug = self._parse_account_ref(name)
        
        vault = self.vaults.get(vault_slug)
        if not vault:
            raise AccountNotFoundError(f"Vault '{vault_slug}' not found.")
            
        return vault.get_account(acc_slug, decrypted=decrypted)

    def save_account(self, account: Account):
        # Determine target vault from name
        vault_slug, acc_slug = self._parse_account_ref(account.name)
        
        # Strip namespace from name before saving
        account.name = acc_slug
        
        vault = self.vaults.get(vault_slug)
        if not vault:
            raise ConfigError(f"Vault '{vault_slug}' does not existence. Cannot save.")
            
        vault.save_account(account)

    def remove_account(self, name: str):
        vault_slug, acc_slug = self._parse_account_ref(name)
        vault = self.vaults.get(vault_slug)
        if not vault:
            raise AccountNotFoundError(f"Vault '{vault_slug}' not found.")
            
        vault.remove_account(acc_slug)
        
        # Update Global Config if active account was removed
        cfg = self.load_config()
        if cfg.active_account:
            active_vault, active_slug_raw = self._parse_account_ref(cfg.active_account)
            # Slugify for robust comparison
            active_slug = slugify(active_slug_raw)
            target_slug = slugify(acc_slug)
            
            if active_vault == vault_slug and active_slug == target_slug:
                cfg.active_account = None
                self.save_config(cfg)

    def delete_account(self, name: str):
        """Alias for remove_account (Legacy compatibility)."""
        self.remove_account(name)

    def switch_account(self, name: str):
        """Switches active account. Validates existence first."""
        # 1. Validate & Normalize
        vault_slug, acc_slug = self._parse_account_ref(name)
        vault = self.vaults.get(vault_slug)
        if not vault:
             raise AccountNotFoundError(f"Vault '{vault_slug}' not found.")
        
        # Check existence in vault (slugifies internally)
        acc = vault.get_account(acc_slug)
        
        # 2. Sync Legacy Auth
        self.sync_legacy_auth(acc)
        
        # 3. Update Config with Canonical Reference
        cfg = self.load_config()
        
        # Canonical: if personal, just slug. If team, team/slug.
        # This keeps 'personal/' implicit for primary accounts as per legacy behavior.
        if vault_slug == "personal":
            cfg.active_account = acc.name # acc.name is slugified local name
        else:
            cfg.active_account = f"{vault_slug}/{acc.name}"
            
        self.save_config(cfg)

    def sync_legacy_auth(self, account: Account):
        """Writes credentials to ~/.codex/auth.json (Legacy Support)."""
        # This logic used to be implicit in `list` or `status` checks.
        # Implementing explicit sync here.
        
        legacy_auth_file = self._get_legacy_auth_file()
        legacy_dir = legacy_auth_file.parent
        legacy_dir.mkdir(parents=True, exist_ok=True)
        
        data = {}
        if account.api_key:
            # Primary key used by this project/tests
            data["api_key"] = account.api_key
            # Compatibility for other tooling
            data["OPENAI_API_KEY"] = account.api_key
        if account.email:
            data["email"] = account.email
        if account.tokens:
            # Preserve nested structure for legacy consumers/tests, and also flatten for convenience.
            data["tokens"] = account.tokens
            data.update(account.tokens)
            
        # Ensure last_refresh is present to satisfy Codex CLI
        data["last_refresh"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            
        with atomic_write(legacy_auth_file) as f:
            f.write(json.dumps(data, indent=2))
        
        
        # Clear sessions to prevent "Token data not available" error
        sessions_dir = legacy_dir / "sessions"
        if sessions_dir.exists():
            shutil.rmtree(sessions_dir)
            sessions_dir.mkdir()  # Recreate empty
        
        os.chmod(legacy_auth_file, 0o600)

    def check_active_integrity(self) -> Dict[str, bool]:
        """Verifies the health of the active account."""
        cfg = self.load_config()
        if not cfg.active_account:
            return {"exists": False, "synced": False, "legacy_exists": False}
        
        try:
            # Check if internal account exists
            acc = self.get_account(cfg.active_account, decrypted=True)
            exists = True
        except Exception:
            exists = False
            legacy_auth_file = self._get_legacy_auth_file()
            return {"exists": False, "synced": False, "legacy_exists": legacy_auth_file.exists()}

        legacy_auth_file = self._get_legacy_auth_file()
        legacy_exists = legacy_auth_file.exists()
        synced = False
        
        if legacy_exists:
            try:
                with open(legacy_auth_file, "r") as f:
                    legacy_data = json.load(f)
                    
                last_refresh_present = "last_refresh" in legacy_data

                legacy_api_key = legacy_data.get("api_key") or legacy_data.get("OPENAI_API_KEY")
                legacy_tokens = legacy_data.get("tokens") or {}
                if not legacy_tokens and acc.tokens:
                    legacy_tokens = {k: legacy_data.get(k) for k in acc.tokens.keys() if k in legacy_data}

                if acc.api_key:
                    synced = (legacy_api_key == acc.api_key) and last_refresh_present
                elif acc.tokens:
                    synced = (legacy_tokens == acc.tokens) and last_refresh_present
                else:
                    synced = last_refresh_present
            except Exception:
                synced = False
                
        return {
            "exists": exists,
            "synced": synced,
            "legacy_exists": legacy_exists
        }
