import typer
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError

app = typer.Typer(help="Manage application context and active account.")

@app.command("switch")
def switch(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of the account to switch to"),
):
    """
    Switch the active account.
    Updates the global configuration and syncs credentials to the legacy auth file.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()

    try:
        mgr.switch_account(name)
        output.success(f"Switched to account '{name}'.")
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)

@app.command("status")
def status(ctx: typer.Context):
    """
    Show current active account.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    
    try:
        config = mgr.load_config()
        slug = config.active_account
        
        if slug:
            output.log(f"Active Account: [bold green]{slug}[/bold green]")
            
            # Integrity Check
            health = mgr.check_active_integrity()
            
            if not health["exists"]:
                output.error(f"Integrity Error: Active account '{slug}' not found in storage!")
            elif not health["synced"]:
                if not health["legacy_exists"]:
                    output.warn("Warning: Legacy auth file missing. Run 'switch' to fix.")
                else:
                    output.warn("Warning: Legacy auth file is out of sync. Run 'switch' to fix.")
            else:
                output.success("Account is synced and ready.")
                
        else:
            output.warn("No active account selected.")
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)
