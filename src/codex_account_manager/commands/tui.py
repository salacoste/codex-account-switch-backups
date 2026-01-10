import typer
import questionary
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError

app = typer.Typer(help="Interactive account browser.")

@app.command("tui")
def tui_cmd(ctx: typer.Context):
    """
    Interactive terminal interface for selecting accounts.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()

    try:
        # Fetch accounts
        accounts = mgr.list_accounts()
        if not accounts:
            output.warn("No accounts found. Use 'add' or 'migrate' first.")
            raise typer.Exit(0)

        # Prepare choices
        choices = [a.name for a in accounts]
        
        # Interactive prompt
        # We assume stdout is a TTY. If not, questionary might struggle, 
        # but typically this command is run interactively.
        selection = questionary.select(
            "Select an account to switch to:",
            choices=choices,
            style=questionary.Style([
                ('qmark', 'fg:#673ab7 bold'),
                ('question', 'bold'),
                ('answer', 'fg:#f44336 bold'),
                ('pointer', 'fg:#673ab7 bold'),
                ('highlighted', 'fg:#673ab7 bold'),
                ('selected', 'fg:#cc545a'),
                ('separator', 'fg:#cc545a'),
                ('instruction', ''),
                ('text', ''),
                ('disabled', 'fg:#858585 italic')
            ])
        ).ask()

        if not selection:
            # User cancelled (Ctrl+C returns None in some versions, or raises error)
            # questionary usually returns None on Ctrl+C if not catching exception
            raise typer.Exit(0)

        # Perform Switch
        mgr.switch_account(selection)
        output.success(f"Switched to account '{selection}'.")

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        output.log("\nCancelled.")
        raise typer.Exit(0)
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)
