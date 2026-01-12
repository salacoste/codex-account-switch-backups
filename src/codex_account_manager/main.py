import sys
import typer
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError
from codex_account_manager.commands import account, context, migrate, tui, hook, portability, sync, run, env, team, local_context, audit, limits

# Initialize app with rich help
app = typer.Typer(
    name="codex-account",
    help="Codex Account Manager - Securely switch and manage Codex authentication.",
    no_args_is_help=True,
    add_completion=True,
)

# ...

# Register Sync commands (Grouping)
app.add_typer(sync.app, name="sync", help="Sync vault with Git repo")
app.add_typer(env.app, name="env", help="Manage env vars for active account")
app.add_typer(team.app, name="team", help="Manage teams and team access")

# Register Local Context commands
# We import local_context as context_cmd to avoid confusion with existing context module?
# Or just use local_context.app
app.add_typer(local_context.app, name="context", help="Manage local directory context")

# Register Audit Command
app.command(name="audit", help="View security audit logs")(audit.view_audit)

# Register Run command (Root)
# Note: we unwrap the command from run.app because we want it at root 
# OR we keep it as run.run but we need to match arguments.
# run.py defines @app.command("run"). If run.app is a Typer app, we can add it.
# app.add_typer(run.app, name="run") -> codex-account run run ?? No.
# we used @app.command("run") in run.py.
# So run.run is the function.
app.command(
    name="run", 
    help="Run command with injected credentials",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)(run.run)

# Helper to register group commands at root
app.command(name="init", help="Initialize account storage")(account.init)
app.command(name="add", help="Add a new account")(account.add)
app.command(name="save", help="Save current login as new account")(account.save)
app.command(name="list", help="List all accounts")(account.list_accounts)
app.command(name="remove", help="Remove an account")(account.remove)
app.command(name="encrypt-all", help="Encrypt all accounts")(account.encrypt_all)

# Register Device Flow commands (Frontend Bridge)
app.command(name="device-login-init", help="[Internal] Init Device Flow")(account.device_login_init)
app.command(name="device-login-poll", help="[Internal] Poll Device Flow")(account.device_login_poll)

# Register Interactive Login
app.command(name="login", help="Interactive login menu")(account.login)

# Register context commands at root level (UX decision: codex-account switch vs codex-account context switch)
app.command(name="switch", help="Switch active account")(context.switch)
app.command(name="status", help="Show current active account")(context.status)
app.command(name="whoami", help="Alias for status")(context.status)

# Register migration command
app.add_typer(migrate.app, name="migrate", help="Import from legacy v2")

# Register TUI commands
app.command(name="tui", help="Interactive account browser")(tui.tui_cmd)
app.command(name="interactive", help="Alias for tui")(tui.tui_cmd)

# Register Hook command
# Register Hook command
app.command(name="hook", help="Detect .codex-account context")(hook.hook_cmd)

# Register Portability commands
app.command(name="export", help="Backup accounts to zip")(portability.export)
app.command(name="import", help="Restore accounts from zip")(portability.import_cmd)

# Register Limits commands
app.add_typer(limits.app, name="limits", help="Examine API usage limits")

@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(
        False, 
        "--json", 
        help="Output machine-readable JSON to stdout."
    ),
    quiet: bool = typer.Option(
        False, 
        "--quiet", 
        "-q", 
        help="Minimal output."
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show debug logs."
    ),
):
    """
    Codex Account Manager - Securely switch and manage Codex authentication.
    -----------------------------------------------------------------------
    Use 'codex-account command --help' for details on specific commands.
    """
    # Initialize OutputManager logic
    # In a real implementation we might configure the manager with quiet/verbose flags
    ctx.obj = OutputManager()
    
    if verbose:
        ctx.obj.log("[dim]Debug mode enabled[/dim]", style="dim")

def main():
    try:
        app()
    except CodexError as e:
        # Known domain error - clean exit
        # Use stderr for visibility without polluting stdout
        sys.stderr.write(f"\033[91mError: {e.message}\033[0m\n")
        sys.exit(e.code)
    except Exception as e:
        # Unexpected error firewall
        sys.stderr.write(f"\033[91mUnexpected Error: {str(e)}\033[0m\n")
        sys.exit(1)

if __name__ == "__main__":
    main()  # pragma: no cover
