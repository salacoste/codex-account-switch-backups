import typer
from pathlib import Path
from codex_account_manager.ingest.legacy import LegacyIngestor
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError, AccountNotFoundError

# Rename local 'app' to 'app' but the command function to 'migrate_cmd' 
# to avoid naming collisions when importing.
app = typer.Typer(help="Migrate accounts from legacy systems.")

@app.command("migrate")
def migrate_cmd(
    ctx: typer.Context,
    source: Path = typer.Option(
        None, "--from", "-f", 
        help="Path to legacy project directory (containing accounts/)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", 
        help="Simulate migration without saving"
    ),
    force: bool = typer.Option(
        False, "--force", 
        help="Overwrite existing accounts if found"
    ),
):
    """
    Import accounts from a legacy 'old-project' directory.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    ingestor = LegacyIngestor()

    if not source:
        # Default to current dir / old-project
        source = Path.cwd() / "old-project"
        output.log("No source specified. Looking for 'old-project' in current directory...")
    
    if not source.exists():
        output.error(f"Source path '{source}' does not exist.")
        raise typer.Exit(code=1)

    output.log(f"Scanning [bold]{source}[/bold]...")

    try:
        # Counters
        found = 0
        imported = 0
        skipped = 0
        
        for account in ingestor.scan(source):
            found += 1
            status_msg = ""
            
            # Check existence
            exists = False
            try:
                mgr.get_account(account.name)
                exists = True
            except AccountNotFoundError:
                exists = False
            
            if exists:
                if not force:
                    output.warn(f"Skipping '{account.name}': Account already exists (use --force to overwrite).")
                    skipped += 1
                    continue
                else:
                    status_msg = " [yellow](Overwriting)[/yellow]"
            
            if dry_run:
                output.log(f"[dim]Dry Run[/dim]: Found account [cyan]{account.name}[/cyan] ({account.email}){status_msg}")
                continue

            try:
                mgr.save_account(account)
                output.success(f"Imported '{account.name}'{status_msg}")
                imported += 1
            except CodexError as e:
                output.warn(f"Failed to save '{account.name}': {e}")
                skipped += 1
        
        # Summary
        if found == 0:
            output.warn("No accounts found in source directory.")
        else:
            if dry_run:
                 output.success(f"Dry run complete. Found {found} accounts.")
            else:
                 output.success(f"Migration complete. Imported {imported}/{found} accounts ({skipped} skipped).")

    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)
