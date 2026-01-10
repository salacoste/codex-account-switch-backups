import typer
from pathlib import Path
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager

app = typer.Typer(help="Manage local directory context (auto-switching).")

CONTEXT_FILENAME = ".codex-context"

@app.command("set")
def set_context(
    ctx: typer.Context,
    account_name: str = typer.Argument(..., help="Account slug to link to this directory")
):
    """
    Link the current directory to a specific account.
    Creates a hidden .codex-context file.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    
    # 1. Verify account exists
    try:
        # We don't need full load, just check existence
        # But get_account handles slugify and validation
        account = manager.get_account(account_name) 
    except Exception:
        output.error(f"Account '{account_name}' does not exist.")
        raise typer.Exit(code=1)
        
    target_file = Path.cwd() / CONTEXT_FILENAME
    
    try:
        target_file.write_text(account.name)
        output.success(f"Linked directory to account [bold]{account.name}[/bold]")
        output.log(f"Created {CONTEXT_FILENAME}")
    except OSError as e:
        output.error(f"Failed to write context file: {e}")
        raise typer.Exit(code=1)

@app.command("show")
def show_context(ctx: typer.Context):
    """
    Show which account is linked to this directory (if any).
    """
    output: OutputManager = ctx.obj
    target_file = Path.cwd() / CONTEXT_FILENAME
    
    if target_file.exists():
        slug = target_file.read_text().strip()
        output.log(f"Local Context: [bold cyan]{slug}[/bold cyan]")
    else:
        output.log("No local context configured for this directory.")

@app.command("clear")
def clear_context(ctx: typer.Context):
    """
    Remove the local link.
    """
    output: OutputManager = ctx.obj
    target_file = Path.cwd() / CONTEXT_FILENAME
    
    if target_file.exists():
        target_file.unlink()
        output.success("Removed local context.")
    else:
        output.warn("No context file found.")
