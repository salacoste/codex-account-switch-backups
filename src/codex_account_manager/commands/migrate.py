"""
Import Legacy Credentials (v2 -> v3 Migration).
"""
import json
import typer
from pathlib import Path
from rich import print

from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account, AccountType

app = typer.Typer(help="Migrate legacy credentials.")

LEGACY_ROOT = Path.home() / ".codex"
LEGACY_AUTH = LEGACY_ROOT / "auth.json"

@app.command("import")
def import_credentials(
    ctx: typer.Context,
    name: str = typer.Option("legacy-imported", "--name", "-n", help="Name for the imported account")
):
    """
    Import credentials from ~/.codex/auth.json (Legacy).
    """
    if not LEGACY_AUTH.exists():
        print(f"[red]Error: Legacy auth file not found at {LEGACY_AUTH}[/red]")
        raise typer.Exit(1)
        
    try:
        with open(LEGACY_AUTH, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
         print(f"[red]Error: Failed to parse {LEGACY_AUTH}[/red]")
         raise typer.Exit(1)
         
    # Fix: ctx.obj is OutputManager, not ConfigManager
    # from codex_account_manager.core.output import OutputManager
    # output: OutputManager = ctx.obj
    
    mgr = ConfigManager()
    
    # Check if account already exists
    try:
        existing = mgr.get_account(name)
        print(f"[yellow]Warning: Account '{name}' already exists in secure storage.[/yellow]")
        if not typer.confirm("Overwrite?"):
            print("Aborted.")
            raise typer.Exit(0)
    except Exception:
        pass # Good, doesn't exist
    
    # Extract Credentials
    api_key = data.get("api_key") or data.get("OPENAI_API_KEY")
    tokens = {}
    
    # Collect standard token fields
    for field in ["access_token", "refresh_token", "id_token", "expires_at", "scope", "token_type"]:
        if field in data:
            tokens[field] = data[field]
            
    # Also collect remaining fields as misc tokens if not api_key
    for k, v in data.items():
        if k not in ["api_key", "OPENAI_API_KEY", "last_refresh"] and k not in tokens:
             tokens[k] = v
            
    if not api_key and not tokens:
        print("[red]Error: No usable credentials found in legacy file.[/red]")
        raise typer.Exit(1)
        
    # Create Account
    account = Account(
        name=name,
        api_key=api_key,
        tokens=tokens if tokens else None,
        type=AccountType.OAUTH if tokens else AccountType.API_KEY,
        tags=["imported", "legacy"]
    )
    
    mgr.save_account(account)
    print(f"[green]Successfully imported '{name}' from {LEGACY_AUTH}![/green]")
    
    # Optional: Set as active
    if typer.confirm(f"Switch to '{name}' now?"):
        mgr.switch_account(name)
        print(f"[green]Active account set to '{name}'.[/green]")
