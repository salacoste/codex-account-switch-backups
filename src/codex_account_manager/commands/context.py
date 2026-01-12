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

    # Check for JSON flag from parent context (main callback)
    is_json = False
    if ctx.parent and ctx.parent.params:
        is_json = ctx.parent.params.get("json_output", False)

    try:
        mgr.switch_account(name)
        if is_json:
            output.print_json({"status": "success", "active_account": name})
        else:
            output.success(f"Switched to account '{name}'.")
    except CodexError as e:
        if is_json:
            output.print_json({"status": "error", "message": e.message})
            raise typer.Exit(code=1)
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
        
        # Check for JSON flag from parent context (main callback)
        is_json = False
        if ctx.parent and ctx.parent.params:
            is_json = ctx.parent.params.get("json_output", False)

        if slug:
            if is_json:
                output.print_json({"active_account": slug, "status": "active"})
            else:
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
            if is_json:
                output.print_json({"active_account": None, "status": "none"})
            else:
                output.warn("No active account selected.")

    except CodexError as e:
        if is_json:
            output.print_json({"error": e.message})
            raise typer.Exit(code=1)
        output.error(e.message)
        raise typer.Exit(code=1)
