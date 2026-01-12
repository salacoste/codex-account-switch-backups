import typer
import asyncio
from rich.table import Table
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.codex_api import CodexAPI
from codex_account_manager.core.exceptions import CodexError

app = typer.Typer(help="Check API usage limits.")

@app.command("show") # Explicit name, but usually invoked as 'codex-account limits'
def show_limits(
    ctx: typer.Context,
    fetch: bool = typer.Option(False, "--fetch", help="Force fetch from API (skip cache)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON")
):
    """
    Display current API usage limits (5-hourly and Weekly).
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    
    try:
        active_slug = mgr.load_config().active_account
        account = mgr.get_account(active_slug)
        
        if not account:
            output.error("No active account.")
            raise typer.Exit(code=1)
            
        # Get Token
        token = None
        if account.api_key:
            token = account.api_key
        elif account.tokens:
             token = account.tokens.get("access_token")
             
        if not token:
             output.error("Active account has no valid credentials.")
             raise typer.Exit(code=1)
             
        # Fetch Logic
        api = CodexAPI(token)
        
        # Async run
        try:
            limits = asyncio.run(api.get_usage_limits())
            # Save to Cache
            try:
                import json
                import time
                from pathlib import Path
                
                cache_file = Path.home() / ".codex-accounts" / "usage_cache.json"
                cache_data = {}
                if cache_file.exists():
                    try:
                        cache_data = json.loads(cache_file.read_text())
                    except:
                        pass # Reset if corrupt
                
                # Update specific account
                cache_data[active_slug] = {
                    "limits": limits,
                    "timestamp": time.time(),
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                
                # Atomic write
                temp_file = cache_file.with_suffix(".tmp")
                temp_file.write_text(json.dumps(cache_data, indent=2))
                temp_file.rename(cache_file)
                
            except Exception as e:
                # Cache failure should not break the command
                if output.verbose:
                    output.warn(f"Failed to update usage cache: {e}")
                    
        except Exception as e:
            output.error(f"Failed to fetch limits: {e}")
            raise typer.Exit(code=1)
            
        if json_output:
            output.print_json(limits)
            return
            
        # Rich Table
        table = Table(title=f"Usage Limits: {account.name}")
        table.add_column("Type", style="cyan")
        table.add_column("Used", justify="right")
        table.add_column("Limit", justify="right")
        table.add_column("Usage %", justify="right")
        table.add_column("Resets In", style="dim")
        
        # 5 Hour
        l5 = limits.get("limit_5h", {})
        used_5 = l5.get("used", 0)
        max_5 = l5.get("limit", 1)
        pct_5 = (used_5 / max_5) * 100
        style_5 = "green" if pct_5 < 80 else "yellow" if pct_5 < 95 else "red"
        reset_5 = f"{l5.get('reset_in_minutes', 0)}m"
        
        table.add_row(
            "5-Hour", 
            str(used_5), 
            str(max_5), 
            f"[{style_5}]{pct_5:.1f}%[/{style_5}]",
            reset_5
        )

        # Weekly
        lw = limits.get("limit_weekly", {})
        used_w = lw.get("used", 0)
        max_w = lw.get("limit", 1)
        pct_w = (used_w / max_w) * 100
        style_w = "green" if pct_w < 80 else "yellow" if pct_w < 95 else "red"
        reset_w = f"{lw.get('reset_in_days', 0)}d"

        table.add_row(
            "Weekly",
            str(used_w),
            str(max_w),
            f"[{style_w}]{pct_w:.1f}%[/{style_w}]",
            reset_w
        )
        
        output.console.print(table)
        
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)
