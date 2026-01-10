import typer
import zipfile
from pathlib import Path
from datetime import datetime
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager

app = typer.Typer(help="Import and Export accounts for backup/migration.")

@app.command("export")
def export(
    ctx: typer.Context,
    target: Path = typer.Option(
        None, 
        "--target", "-t", 
        help="Path where the backup zip will be saved. Defaults to ./codex-backup-YYYYMMDD.zip"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Overwrite existing file without confirmation")
):
    """
    Export all accounts to a secure zip archive.
    WARNING: The archive contains your encrypted credentials. 
    You MUST have the same Master Key to decrypt them on another machine.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    
    if not target:
        timestamp = datetime.now().strftime("%Y%m%d")
        target = Path(f"./codex-backup-{timestamp}.zip")
        
    # Check if target exists
    if target.exists() and not yes:
        if not typer.confirm(f"File '{target}' already exists. Overwrite?"):
            output.log("Operation cancelled.")
            raise typer.Exit(code=0)
            
    accounts_dir = manager.accounts_dir
    if not accounts_dir.exists() or not any(accounts_dir.iterdir()):
        output.warn("No accounts found to export.")
        return

    try:
        count = 0
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            with output.console.status(f"[bold green]Backing up to {target}...[/bold green]"):
                for account_path in accounts_dir.iterdir():
                    if account_path.is_dir():
                        slug = account_path.name
                        for file in account_path.iterdir():
                            if file.is_file() and file.name != ".DS_Store":
                                arcname = f"{slug}/{file.name}"
                                zf.write(file, arcname)
                        count += 1
                        
        output.success(f"Exported {count} accounts to [bold]{target}[/bold]")
        output.log("[dim]Note: Restore using 'codex-account import <file>'[/dim]")
        
    except Exception as e:
        output.error(f"Export failed: {e}")
        if target.exists() and count == 0: 
            # If nothing written and failed, maybe cleanup?
            pass
        raise typer.Exit(code=1)

@app.command("import")
def import_cmd(
    ctx: typer.Context,
    target: Path = typer.Argument(..., help="Path to backup zip file"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Overwrite existing accounts without confirmation")
):
    """
    Import accounts from a backup zip archive.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    
    if not target.exists():
        output.error(f"Backup file '{target}' not found.")
        raise typer.Exit(code=1)
        
    try:
        if not zipfile.is_zipfile(target):
            output.error(f"File '{target}' is not a valid zip archive.")
            raise typer.Exit(code=1)
            
        with zipfile.ZipFile(target, 'r') as zf:
            # 1. Validation phase
            valid_accounts = set()
            for name in zf.namelist():
                parts = Path(name).parts
                if len(parts) >= 2 and parts[1] == "auth.enc":
                    valid_accounts.add(parts[0])
                    
            if not valid_accounts:
                output.warn("No valid encrypted accounts found in archive.")
                return

            output.log(f"Found [bold]{len(valid_accounts)}[/bold] accounts in backup.")
            
            # 2. Extraction phase
            imported_count = 0
            skipped_count = 0
            
            for slug in valid_accounts:
                target_dir = manager.accounts_dir / slug
                
                # Check collision
                if target_dir.exists():
                    if not yes:
                        should_overwrite = typer.confirm(f"Account '{slug}' already exists. Overwrite?")
                        if not should_overwrite:
                            output.log(f"[dim]Skipped '{slug}'[/dim]")
                            skipped_count += 1
                            continue
                            
                # Extraction
                # We extract files starting with slug/
                for member in zf.namelist():
                    if member.startswith(f"{slug}/"):
                        p = Path(member)
                        if len(p.parts) < 2:
                            continue
                        
                        rel_path = Path(*p.parts[1:]) 
                        out_path = target_dir / rel_path
                        
                        if member.endswith("/"): 
                            out_path.mkdir(parents=True, exist_ok=True)
                        else:
                            out_path.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(member) as source, open(out_path, "wb") as dest:
                                dest.write(source.read())
                                
                imported_count += 1
                
            if imported_count > 0:
                output.success(f"Successfully imported {imported_count} accounts.")
            if skipped_count > 0:
                output.warn(f"Skipped {skipped_count} existing accounts.")
                
    except Exception as e:
        output.error(f"Import failed: {e}")
        raise typer.Exit(code=1)
