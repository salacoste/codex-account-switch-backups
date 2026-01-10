import typer
import subprocess
import os
from typing import List
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager

# We want "run" to handle arbitrary args, so we use context.args usually?
# Or just separate args.
# Typer supports "run [ARGS]..." via `args: List[str]`

app = typer.Typer(help="Run commands with injected credentials.")

@app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    cmd_args: List[str] = typer.Argument(None, help="Command to run, e.g. -- python script.py")
):
    """
    Run a command with credentials injected from the active account.
    
    Example:
      codex-account run -- aws s3 ls
      codex-account run -- printenv CODEX_API_KEY
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    
    # 1. Get Active Account
    cfg = manager.load_config()
    if not cfg.active_account:
        output.error("No active account selected.")
        raise typer.Exit(code=1)
        
    try:
        account = manager.get_account(cfg.active_account)
    except Exception as e:
        output.error(f"Failed to load active account '{cfg.active_account}': {e}")
        raise typer.Exit(code=1)
        
    # 2. Build Environment
    env = os.environ.copy()
    
    # Inject Custom Vars
    if account.env_vars:
        env.update(account.env_vars)
        
    # Inject Standard Mappings (if present)
    if account.api_key:
        env["CODEX_API_KEY"] = account.api_key
        # Backwards compat: maybe OPENAI_API_KEY if we want to be opinionated?
        # Story 13.1 said only mapped to CODEX_API_KEY by default.
        
    if account.tokens:
        if "access_token" in account.tokens:
            env["CODEX_ACCESS_TOKEN"] = account.tokens["access_token"]
            
    # 3. Execute Command
    # cmd_args is list of strings.
    if not cmd_args:
        output.error("No command provided.")
        raise typer.Exit(code=1)
        
    # If user used "--", cmd_args captures everything after it properly.
    
    output.log(f"[dim]Running in context: [bold]{account.name}[/bold][/dim]")
    
    try:
        # We use subprocess.run to wait for completion.
        # We assume shell=False for safety, user provides list.
        # stdin/out/err are inherited by default.
        result = subprocess.run(cmd_args, env=env)
        
        # Propagate exit code
        raise typer.Exit(code=result.returncode)
        
    except FileNotFoundError:
        output.error(f"Command not found: {cmd_args[0]}")
        raise typer.Exit(code=127)
    except KeyboardInterrupt:
        output.warn("Interrupted.")
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception as e:
        output.error(f"Execution failed: {repr(e)}")
        raise typer.Exit(code=1)
