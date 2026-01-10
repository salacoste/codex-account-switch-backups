import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(help="Shell integration hooks.")

def find_local_config(start_path: Path) -> Optional[Path]:
    """
    Recursively search for .codex-account in current and parent directories.
    Stops at the filesystem root.
    """
    # current = start_path.absolute() # Remove absolute to trust input path
    current = start_path
    
    # Safety check for infinite loops (though pathlib handles parents well)
    while True:
        target = current / ".codex-account"
        if target.exists() and target.is_file():
            return target
        
        parent = current.parent
        if parent == current:
            # Reached root
            return None
        current = parent

@app.command("hook")
def hook_cmd(
    ctx: typer.Context, 
    path: Path = typer.Option(
        None, "--path", "-p", 
        help="Path to start searching from (defaults to CWD)"
    )
):
    """
    Detect local account configuration.
    
    Searches for a .codex-account file in the current or parent directories.
    If found, prints the account name to stdout.
    If not found, exits with status 1.
    """
    start_dir = Path(path) if path else Path.cwd()
    # print(f"DEBUG: Start Dir: {start_dir}")
    
    config_file = find_local_config(start_dir)
    
    if config_file:
        try:
            # Read single line, strip whitespace
            content = config_file.read_text().strip()
            if content:
                typer.echo(content)
                # Success found
                raise typer.Exit(code=0)
        except typer.Exit:
            raise
        except Exception:
            # If unreadable, treat as not found
            pass
            
    # Not found or empty
    raise typer.Exit(code=1)
