from pathlib import Path
from typing import Generator
import json
from codex_account_manager.config.models import Account
from codex_account_manager.core.exceptions import CodexError

class LegacyIngestor:
    """
    Parses legacy 'old-project' directory structures.
    Does NOT write to config directly (separation of concerns).
    Returns Account objects for the caller to save.
    """
    
    def scan(self, path: Path) -> Generator[Account, None, None]:
        """
        Scans a directory for legacy account structures.
        Expected structure: <root>/accounts/<name>/auth.json
        """
        if not path.exists():
            raise CodexError(f"Migration source '{path}' does not exist.")
            
        accounts_dir = path / "accounts"
        if not accounts_dir.exists():
            # Try direct scan of subdirs if 'accounts' doesn't exist?
            # Or strict adherence to known structure?
            # Strict for now to avoid garbage ingestion.
            raise CodexError(f"Source '{path}' does not look like a legacy project (missing 'accounts/' dir).")
            
        for account_item in accounts_dir.iterdir():
            if not account_item.is_dir():
                continue
                
            # Account name is directory name
            name = account_item.name
            
            # Check for metadata file (account.json)
            # If not found, it's likely not a valid account dir (or just _template)
            account_meta = account_item / "account.json"
            if not account_meta.exists():
                continue

            # Look for credentials in backups/
            # We want the LATEST backup
            backups_dir = account_item / "backups"
            if not backups_dir.exists():
                # Fallback: maybe auth.json exists in root (PRD assumption mismatch?)
                # If no backups and no auth.json, we can't migrate credentials.
                auth_file = account_item / "auth.json"
            else:
                backups = sorted(backups_dir.glob("*auth.json"))
                auth_file = backups[-1] if backups else None

            if auth_file and auth_file.exists():
                try:
                    with open(auth_file, "r") as f:
                        data = json.load(f)
                        
                    # Support both standard and legacy key names
                    api_key = data.get("api_key") or data.get("OPENAI_API_KEY")
                    tokens = data.get("tokens")
                    
                    # Must have at least one credential type
                    if not api_key and not tokens:
                        continue
                        
                    email = data.get("email", None)
                    
                    yield Account(name=name, email=email, api_key=api_key, tokens=tokens)
                    
                except (json.JSONDecodeError, KeyError):
                    continue # Skip corrupted files
