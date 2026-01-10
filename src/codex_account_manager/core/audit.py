import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

class AuditManager:
    def __init__(self, root_path: Optional[Path] = None):
        if root_path is None:
            # Default to standard location if not provided
            root_path = Path.home() / ".codex-accounts"
            
        self.log_file = root_path / "audit.log"
        self._ensure_dir()

    def _ensure_dir(self):
        if not self.log_file.parent.exists():
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event_type: str, account: str, details: Optional[Dict[str, Any]] = None, success: bool = True):
        """
        Log an audit event.
        
        Args:
            event_type: e.g. "access", "modify", "delete"
            account: The account slug involved
            details: Extra metadata (command, specific fields, etc)
            success: Whether the operation succeeded
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "account": account,
            "success": success,
            "details": details or {}
        }
        
        try:
            # Append to file (thread-safe enough for CLI usage generally)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            # Silently fail? Or print to stderr?
            # For audit logs, failure to log is bad, but crashing the app is worse?
            # We'll print a warning to stderr generally, but here we don't have OutputManager.
            pass

    def get_events(self, limit: int = 50):
        """Read last N events."""
        if not self.log_file.exists():
            return []
            
        lines = []
        try:
            # Efficient implementation for large files would be `tail` but simple Readlines is fine for MVP
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return []
            
        # Parse last N
        events = []
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
                
        # Reverse to show newest first? Or preserve order?
        # Usually viewers want newest first.
        return list(reversed(events))
