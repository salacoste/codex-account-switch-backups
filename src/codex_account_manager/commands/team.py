import typer
import subprocess
import shutil
from rich.prompt import Prompt

from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.utils import slugify

app = typer.Typer(name="team", help="Manage shared team vaults.")

@app.command("join")
def join_team(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Local name for the team (e.g. 'ops')"),
    repo_url: str = typer.Argument(..., help="Git URL of the team vault"),
):
    """
    Join a shared team vault via Git.
    Requires the Team Master Key (provided by your admin).
    """
    output: OutputManager = ctx.obj
    mgr = ConfigManager()
    
    slug = slugify(name)
    if slug == "personal":
        output.error("Cannot name a team 'personal'. Reserved.")
        raise typer.Exit(1)
        
    # Check simple collision
    if slug in mgr.config.mounts:
        output.error(f"Team '{slug}' is already mounted.")
        raise typer.Exit(1)
        
    output.log(f"Joining team [bold cyan]{slug}[/bold cyan] from {repo_url}...")
    
    # 1. Ask for Key
    key_str = Prompt.ask("Enter Team Master Key (hidden)", password=True)
    if not key_str:
        output.error("Key is required.")
        raise typer.Exit(1)
        
    # validate key format roughly? Fernet keys are 44 chars base64.
    if len(key_str) < 32:
        output.warn("Warning: Key seems short. Ensure it's a valid Fernet key.")
        
    # 2. Clone Repo
    # We clone into ~/.codex-accounts/teams/<slug>
    teams_root = mgr.root / "teams"
    target_dir = teams_root / slug
    
    if target_dir.exists():
        output.error(f"Target directory {target_dir} already exists. Remove it first.")
        raise typer.Exit(1)
        
    teams_root.mkdir(parents=True, exist_ok=True)
    
    try:
        # We use subprocess for git
        # Security: Repo URL safe? 
        subprocess.run(
            ["git", "clone", repo_url, str(target_dir)], 
            check=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        output.error("Failed to clone repository. Check URL and SSH keys.")
        raise typer.Exit(1)
    except FileNotFoundError:
        output.error("git command not found. Please install git.")
        raise typer.Exit(1)
        
    # 3. Encrypt & Save Key
    try:
        # Encrypt the team key using Primary Key
        # ConfigManager has self.crypto initialized with Primary Key
        encrypted_key_bytes = mgr.crypto.encrypt(key_str)
        # Store as hex string in JSON
        encrypted_key_hex = encrypted_key_bytes.hex()
        
        cfg = mgr.load_config()
        cfg.mounts[slug] = str(target_dir)
        cfg.team_keys[slug] = encrypted_key_hex
        mgr.save_config(cfg)
        
        output.success(f"Successfully joined team '{slug}'!")
        output.log("Access accounts via: [bold]codex-account list[/bold]")
        
    except Exception as e:
        # Cleanup on fail
        if target_dir.exists():
            shutil.rmtree(target_dir)
        output.error(f"Failed to save configuration: {e}")
        raise typer.Exit(1)
