import typer
from rich.table import Table
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager

app = typer.Typer(help="Manage environment variables for the active account.")

def _get_active_account(ctx: typer.Context):
    """Helper to get active account and manager."""
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    
    cfg = manager.load_config()
    if not cfg.active_account:
        output.error("No active account selected.")
        raise typer.Exit(code=1)
        
    try:
        account = manager.get_account(cfg.active_account)
        return manager, account
    except Exception as e:
        output.error(f"Failed to load active account: {e}")
        raise typer.Exit(code=1)

@app.command("add")
def add(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Environment variable name (e.g. AWS_REGION)"),
    value: str = typer.Argument(..., help="Value to store")
):
    """
    Add or update an environment variable for the active account.
    """
    output: OutputManager = ctx.obj
    manager, account = _get_active_account(ctx)
    
    # Update dict
    account.env_vars[key] = value
    
    try:
        manager.save_account(account)
        output.success(f"Set [bold]{key}[/bold] for account '{account.name}'")
    except Exception as e:
        output.error(f"Failed to save account: {e}")
        raise typer.Exit(code=1)

@app.command("remove")
def remove(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Key to remove")
):
    """
    Remove an environment variable.
    """
    output: OutputManager = ctx.obj
    manager, account = _get_active_account(ctx)
    
    if key not in account.env_vars:
        output.warn(f"Key '{key}' not found.")
        return
        
    del account.env_vars[key]
    
    try:
        manager.save_account(account)
        output.success(f"Removed [bold]{key}[/bold]")
    except Exception as e:
        output.error(f"Failed to save account: {e}")
        raise typer.Exit(code=1)

@app.command("list")
def list_vars(ctx: typer.Context):
    """
    List configured environment variables.
    """
    output: OutputManager = ctx.obj
    manager, account = _get_active_account(ctx)
    
    if not account.env_vars:
        output.log("No custom environment variables configured.")
        return
        
    table = Table(title=f"Env Vars ({account.name})")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")
    
    for k, v in account.env_vars.items():
        # Mask value?
        masked_val = v
        if len(v) > 8:
            masked_val = f"{v[:4]}...{v[-4:]}"
        elif len(v) > 4:
            masked_val = f"{v[:2]}..."
            
        table.add_row(k, masked_val)
        
    output.console.print(table)
