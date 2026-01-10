import typer
import json
from rich.table import Table
from datetime import datetime
from codex_account_manager.core.audit import AuditManager
from codex_account_manager.core.output import OutputManager

app = typer.Typer(help="View access logs.")

@app.command("audit")
def view_audit(
    ctx: typer.Context,
    limit: int = typer.Option(50, "--limit", "-n", help="Number of events to show"),
    account: str = typer.Option(None, "--account", help="Filter by account slug")
):
    """
    View recent security events (access logs).
    """
    output: OutputManager = ctx.obj
    audit = AuditManager()
    
    events = audit.get_events(limit=limit)
    
    if not events:
        output.log("No audit events found.")
        return
        
    table = Table(title="Audit Log")
    table.add_column("Timestamp", style="dim")
    table.add_column("Event", style="bold")
    table.add_column("Account", style="cyan")
    table.add_column("Details")
    
    count = 0
    for e in events:
        if account and e.get("account") != account:
            continue
            
        ts = e.get("timestamp", "")
        # Try to format TS nicer?
        try:
            dt = datetime.fromisoformat(ts)
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts_str = ts
            
        details = json.dumps(e.get("details", {}))
        # Determine color for event
        evt_style = "white"
        if e["event"] == "delete":
            evt_style = "red"
        elif e["event"] == "modify":
            evt_style = "yellow"
        elif e["event"] == "accessDecrypted":
            evt_style = "green"
            
        table.add_row(ts_str, f"[{evt_style}]{e['event']}[/{evt_style}]", e.get("account", "-"), details)
        count += 1
        
    if count == 0:
        output.log("No events match filter.")
    else:
        output.console.print(table)
