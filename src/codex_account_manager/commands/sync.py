import typer
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError

app = typer.Typer(help="Sync your vault with a private Git repository.")

def _run_git(args: list[str], cwd: Path) -> str:
    """Helper to run git commands."""
    if not shutil.which("git"):
        raise CodexError("Git is not installed or not in PATH.")
        
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Pass through git error
        raise CodexError(f"Git error: {e.stderr.strip()}")

@app.command("init")
def init(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="Remote Git repository URL (HTTPS or SSH)"),
):
    """
    Initialize Git synchronization for the vault.
    Sets up a private repo in ~/.codex-accounts and connects to remote.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    root = manager.root
    
    output.log(f"Initializing Git repo in [bold]{root}[/bold]...")
    
    try:
        # 1. Init
        if not (root / ".git").exists():
            _run_git(["init"], cwd=root)
            output.log("Initialized local git repository.")
        else:
            output.log("Git repository already initialized.")
            
        # 2. Configure Remote
        try:
            current_remote = _run_git(["remote", "get-url", "origin"], cwd=root)
            if current_remote != url:
                _run_git(["remote", "set-url", "origin", url], cwd=root)
                output.success(f"Updated remote 'origin' to {url}")
            else:
                output.log("Remote 'origin' already matches.")
        except CodexError:
            # Remote likely doesn't exist
            _run_git(["remote", "add", "origin", url], cwd=root)
            output.success(f"Added remote 'origin': {url}")
            
        # 3. Configure .gitignore for Security
        gitignore = root / ".gitignore"
        # We need to allowlist encrypted files while blocking everything else
        # Current default is "*\n!.gitignore"
        # We want to add:
        # !accounts/**/auth.enc
        # !accounts/**/account.json (if we support legacy sync, but better not?)
        # For v1.6, we only sync *.enc
        
        needed_rules = {
            "!accounts/**/auth.enc",
            "!cloud-config.json" # Future proof?
        }
        
        current_content = gitignore.read_text() if gitignore.exists() else "*\n!.gitignore\n"
        new_content = current_content
        updated = False
        
        for rule in needed_rules:
            if rule not in current_content:
                new_content += f"\n{rule}"
                updated = True
                
        if updated:
            gitignore.write_text(new_content)
            output.success("Updated .gitignore to allowlist encrypted files.")
            
        output.warn("[bold red]IMPORTANT:[/bold red] Make sure you backup your 'master.key' separately! It is NOT synced.")
        
    except Exception as e:
        output.error(f"Sync Init failed: {e}")
        raise typer.Exit(code=1)

@app.command("push")
def push(ctx: typer.Context):
    """
    Push local changes to the remote repository.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    root = manager.root
    
    if not (root / ".git").exists():
        output.error("Git not initialized. Run 'codex-account sync init <url>' first.")
        raise typer.Exit(code=1)
        
    try:
        with output.console.status("Syncing to cloud..."):
            # Add changes
            _run_git(["add", "."], cwd=root)
            
            # Check if there are changes to commit
            status = _run_git(["status", "--porcelain"], cwd=root)
            if status:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _run_git(["commit", "-m", f"Sync: {timestamp}"], cwd=root)
                output.log("Commited changes.")
            
            # Push
            _run_git(["push", "-u", "origin", "master"], cwd=root) # or main? git init defaults vary. 
            # Modern git defaults to main? Or user config? 
            # We can detect branch:
            branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
            _run_git(["push", "-u", "origin", branch], cwd=root)
            
        output.success("Successfully synced to remote.")
        
    except Exception as e:
        output.error(f"Push failed: {e}")
        raise typer.Exit(code=1)

@app.command("pull")
def pull(
    ctx: typer.Context, 
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite local changes if conflicts occur")
):
    """
    Pull changes from the remote repository.
    """
    output: OutputManager = ctx.obj
    manager = ConfigManager()
    root = manager.root
    
    if not (root / ".git").exists():
        output.error("Git not initialized. Run 'codex-account sync init <url>' first.")
        raise typer.Exit(code=1)
        
    try:
        with output.console.status("Pulling from cloud..."):
            branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
            
            # Fetch first
            _run_git(["fetch", "origin"], cwd=root)
            
            # Pull logic
            # Use --rebase to keep linear history? 
            # Or --no-edit to merge?
            # If force is True, we might want to reset hard?
            
            if force:
                _run_git(["reset", "--hard", f"origin/{branch}"], cwd=root)
                output.warn("Forced reset to remote state.")
            else:
                _run_git(["pull", "origin", branch], cwd=root)
                
        output.success("Successfully pulled from remote.")
        
    except Exception as e:
        output.error(f"Pull failed: {e}")
        output.log("Try --force to overwrite local changes.")
        raise typer.Exit(code=1)
