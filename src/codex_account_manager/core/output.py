from rich.console import Console
from typing import Any, Optional

class OutputManager:
    """
    Manages all output to the terminal, enforcing the 'Clean Pipe' rule.
    - stdout: Reserved for requested machine-readable data (JSON) or direct table output.
    - stderr: Reserved for logs, status messages, spinners, and human interaction.
    """
    def __init__(self):
        # stderr console for human logs/interaction
        self.console = Console(stderr=True)
        # stdout console for data piping
        self.stdout = Console(stderr=False)

    def print_json(self, data: Any):
        """Prints pure JSON to stdout."""
        self.stdout.print_json(data=data)

    def log(self, message: str, style: Optional[str] = None):
        """Logs a message to stderr."""
        self.console.print(message, style=style)

    def success(self, message: str):
        """Logs a success message to stderr."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def error(self, message: str):
        """Logs an error message to stderr."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def warn(self, message: str):
        """Logs a warning to stderr."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
