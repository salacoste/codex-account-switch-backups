import typer
import questionary
from typing import Optional, List
from rich.table import Table
import json
import os
from pathlib import Path
from codex_account_manager.config.manager import ConfigManager, LEGACY_AUTH_FILE
from codex_account_manager.config.models import Account, AccountType
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError
from codex_account_manager.commands.auth import DeviceAuth

app = typer.Typer(help="Manage Codex accounts (add, list, remove).")

@app.command("login")
def login(ctx: typer.Context):
    """
    Interactive login menu: Switch accounts or Add New via Browser.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    
    # 1. Prepare Menu Options
    try:
        accounts = mgr.list_accounts()
    except CodexError:
        accounts = []
        
    choices = ["➕ Add New Account"]
    
    # Add existing accounts to menu
    # Format: "name (active)" if active, else "name"
    active_slug = mgr.load_config().active_account
    
    account_map = {} # Display Name -> Real Slug
    
    for acc in accounts:
        display = acc.name
        if acc.name == active_slug:
            display = f"{acc.name} (active)"
        
        # Add icons based on type
        if hasattr(acc, 'type'):
             if acc.type == AccountType.API_KEY:
                 display = f"🔑 {display}"
             elif acc.type == AccountType.OAUTH:
                 display = f"👤 {display}"

        choices.append(display)
        account_map[display] = acc.name

    # 2. Show Menu
    selection = questionary.select(
        "Select an account to log in:",
        choices=choices
    ).ask()
    
    if not selection:
        raise typer.Exit(code=0) # Cancelled
        
    # 3. Handle "Add New"
    if selection == "➕ Add New Account":
        _handle_new_login(output, mgr)
        return

    # 4. Handle Switch
    target_slug = account_map[selection]
    if target_slug == active_slug:
        output.success(f"Already logged in to '{target_slug}'.")
        return
        
    try:
        mgr.switch_account(target_slug)
        output.success(f"Switched to account '{target_slug}'.")
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)

def _handle_new_login(output: OutputManager, mgr: ConfigManager):
    """
    Orchestrates the Device Flow login and saving.
    """
    auth = DeviceAuth()
    
    # 1. Initiate
    try:
        output.log("[bold cyan]Initiating browser login...[/bold cyan]")
        flow_data = auth.initiate_flow()
    except CodexError as e:
        output.error(f"Could not start login: {e}")
        raise typer.Exit(code=1)
        
    # 2. Display Instructions
    output.console.print("\n[bold yellow]Please complete the login in your browser:[/bold yellow]")
    output.console.print(f"URL:  [link={flow_data['verification_uri']}]{flow_data['verification_uri']}[/link]")
    output.console.print(f"Code: [bold green]{flow_data['user_code']}[/bold green]\n")
    
    # 3. Poll
    with output.console.status("Waiting for authorization..."):
        try:
            tokens = auth.poll_for_token(
                flow_data['device_code'], 
                interval=flow_data['interval']
            )
        except CodexError as e:
            output.error(str(e))
            raise typer.Exit(code=1)
            
    output.success("Authentication successful!")
    
    # 4. Identify User
    try:
        user_info = auth.get_user_info(tokens['access_token'])
        email = user_info.get("email")
        if not email:
            email = typer.prompt("Could not detect email. Please enter a name for this account")
    except CodexError:
        email = typer.prompt("Failed to fetch profile. Enter name/email for account")

    # 5. Save
    # Propose default name from email
    default_name = email.split("@")[0]
    name = typer.prompt("Save account as", default=default_name)
    
    # Construct Account
    # We map OIDC tokens to our internal structure
    # Tokens dict from Auth0 usually has access_token, refresh_token, id_token, expires_in key
    
    account = Account(
        name=name,
        email=email,
        type=AccountType.OAUTH,
        tokens=tokens, # Save full blob
        tags=["oauth"]
    )
    
    try:
        mgr.save_account(account)
        output.success(f"Account '{name}' saved and encrypted.")
        
        # Auto-switch
        mgr.switch_account(name)
        output.success(f"Switched to '{name}'. You are ready to go!")
        
    except CodexError as e:
        output.error(f"Failed to save account: {e.message}")
        raise typer.Exit(code=1)

@app.command("init")
def init(ctx: typer.Context):
    """
    Initialize the account storage directory.
    """
    output: OutputManager = ctx.obj
    try:
        # ConfigManager init handles directory creation and security
        ConfigManager()
        output.success(f"Initialized storage at {ConfigManager().root}")
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)

@app.command("add")
def add(
    ctx: typer.Context,
    name: str = typer.Argument(None, help="Unique name for the account (slug)"),
    email: str = typer.Option(None, help="Email address"),
    api_key: str = typer.Option(None, help="Codex API Key"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Tags for categorization"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing account"),
):
    """
    Add a new Codex account.
    Launches an interactive wizard if arguments are missing.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    is_interactive = False

    # Interactive Wizard
    if not name:
        output.log("[bold]Add New Account[/bold]")
        name = typer.prompt("Account Name (e.g. 'work', 'personal')")
        is_interactive = True
    
    # Check existence
    try:
        existing = mgr.get_account(name)
        if existing and not force:
            output.error(f"Account '{name}' already exists. Use --force to overwrite.")
            raise typer.Exit(code=1)
    except CodexError:
        pass # Good, doesn't exist

    if not email:
        email = typer.prompt("Email")
        is_interactive = True
    
    if not api_key:
        api_key = typer.prompt("API Key", hide_input=True)
        is_interactive = True

    if not tags and is_interactive:
        # Prompt for tags if not provided via flags (optional)
        tags_input = typer.prompt("Tags (comma separated, optional)", default="", show_default=False)
        if tags_input:
            tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        else:
            tags = []
    elif not tags:
        tags = []

    # Create & Save
    account = Account(name=name, email=email, api_key=api_key, tags=tags)
    try:
        mgr.save_account(account)
        output.success(f"Account '{account.name}' added successfully.")
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)

@app.command("save")
def save(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name for the new account"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing"),
):
    """
    Save the currently logged-in state (from ~/.codex/auth.json) as a new account.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()

    # Determine auth file path
    legacy_path = Path(os.path.expanduser(str(LEGACY_AUTH_FILE)))
    
    if not legacy_path.exists():
        output.error(f"No auth file found at {legacy_path}. Please login locally first.")
        raise typer.Exit(code=1)

    try:
        with open(legacy_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        output.error(f"Auth file at {legacy_path} is corrupted.")
        raise typer.Exit(code=1)

    # Extract credentials
    api_key = data.get("api_key") or data.get("OPENAI_API_KEY")
    tokens = data.get("tokens")
    email = data.get("email")

    if not api_key and not tokens:
        if "access_token" in data:
            tokens = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "id_token": data.get("id_token"),
                "expires_at": data.get("expires_at"),
            }
            tokens = {k: v for k, v in tokens.items() if v is not None}

    if not api_key and not tokens:
        output.error("No valid credentials found in auth file.")
        raise typer.Exit(code=1)

    # Check existence
    try:
        existing = mgr.get_account(name)
        if existing and not force:
            output.error(f"Account '{name}' already exists. Use --force to overwrite.")
            raise typer.Exit(code=1)
    except CodexError:
        pass

    # Create & Save
    account = Account(
        name=name, 
        email=email, 
        api_key=api_key, 
        tokens=tokens,
        tags=[]
    )

    try:
        mgr.save_account(account)
        output.success(f"Saved current session as account '{name}'.")
    except CodexError as e:
        output.error(f"Failed to save account: {e.message}")
        raise typer.Exit(code=1)

@app.command("list")
def list_accounts(
    ctx: typer.Context,
    show_secrets: bool = typer.Option(False, "--show-secrets", help="Show API keys in output (Dangerous!)"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """
    List all configured accounts.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    
    try:
        accounts = mgr.list_accounts()
        
        # Filter by tag if requested
        if tag:
            accounts = [a for a in accounts if tag in a.tags]
            
        config = mgr.load_config()
        active_slug = config.active_account
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)

    # JSON Output handled by main callback flag? 
    # Typer doesn't pass the parent context's json flag automatically unless we check it.
    # Architecture says OutputManager handles this check? 
    # Actually, main.py checks the flag but didn't set a global state on OutputManager logic.
    # Refinement: OutputManager should expose a 'is_json' check or we handle it here.
    # For now, let's assume OutputManager.print_json handles formatting if we pass data.
    
    # We need to respect the global --json flag. 
    # In main.py: `ctx.obj = OutputManager()`. It didn't store the JSON preference.
    # We should probably check if we can access the parent, or if Output.print_json is smart.
    # The current OutputManager implementation has `stdout` and `console`.
    # Let's check `ctx.parent.params['json_output']` (a bit hacky) or just print robust table.
    
    # JSON Output 
    is_json = ctx.parent.params.get('json_output', False)

    if is_json:
        data = [a.model_dump(mode='json', exclude_none=True) for a in accounts]
        if not show_secrets:
            for d in data:
                d['api_key'] = '********'
                if d.get('tokens'):
                    d['tokens'] = {k: '********' for k in d['tokens']}
        output.print_json(data)
        return

    # Rich Table Output
    table = Table(title="Codex Accounts")
    table.add_column("Active", justify="center", style="bold green")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Tags", style="magenta")
    table.add_column("Email")
    table.add_column("Created")
    
    if show_secrets:
        table.add_column("Credential", style="red")

    if not accounts:
        output.warn("No accounts found. Run 'codex-account add'.")
        return

    for acc in accounts:
        is_active = "✓" if acc.name == active_slug else ""
        tags_str = ", ".join(acc.tags) if acc.tags else ""
        
        # Determine Credential display
        credential_display = ""
        if show_secrets:
            if acc.api_key:
                credential_display = acc.api_key
            elif acc.tokens:
                token = acc.tokens.get("access_token", "???")
                # Truncate long tokens for display
                if len(token) > 20:
                    credential_display = f"{token[:10]}...{token[-5:]} (OAuth)"
                else:
                    credential_display = token
            else:
                credential_display = "Empty"

        row = [
            is_active, 
            acc.name, 
            acc.type.value if hasattr(acc, 'type') else "api_key",
            tags_str, 
            acc.email or "", 
            acc.created_at.strftime("%Y-%m-%d")
        ]
        
        if show_secrets:
            row.append(credential_display)
            
        table.add_row(*row)

    output.console.print(table)

@app.command("remove")
def remove(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of account to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """
    Permanently remove an account.
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()

    try:
        # Verify existence
        mgr.get_account(name)
        
        if not force:
            if not typer.confirm(f"Are you sure you want to delete account '{name}'?"):
                output.log("Operation cancelled.")
                raise typer.Exit(code=0)

        mgr.delete_account(name)
        output.success(f"Account '{name}' removed.")
        
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)

@app.command("encrypt-all")
def encrypt_all(
    ctx: typer.Context,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Migrates all accounts to the encrypted format.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager() # Reuse standard init (ctx.obj might be OutputManager)
    
    # Check if context has config manager? 
    # Standard pattern in this file seems to be re-initing ConfigManager() or using ctx.obj if it IS a ConfigManager?
    # In list/remove we did `output: OutputManager = ctx.obj` AND `mgr = ConfigManager()`.
    # Let's stick to that pattern.
    
    try:
        accounts = manager.list_accounts()
        if not accounts:
            output.warn("No accounts found to encrypt.")
            return

        output.log(f"Found [bold]{len(accounts)}[/bold] accounts.")
        if not yes:
            if not typer.confirm("This will encrypt all account files on disk. Continue?"):
                output.log("Operation cancelled.")
                raise typer.Exit(code=0)
        
        success_count = 0
        with output.console.status("[bold green]Encrypting accounts...[/bold green]"):
            for acc in accounts:
                try:
                    # save_account implementation handles encryption and legacy cleanup
                    manager.save_account(acc)
                    success_count += 1
                    output.console.print(f"  [green]✓[/green] Encrypted [bold]{acc.name}[/bold]")
                except Exception as e:
                    output.error(f"Failed to encrypt {acc.name}: {e}")
                    
        output.success(f"Successfully encrypted {success_count}/{len(accounts)} accounts.")
        
    except CodexError as e:
        output.error(e.message)
        raise typer.Exit(code=1)
