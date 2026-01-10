import re
import os
import contextlib
from pathlib import Path
from typing import Generator, Any

def slugify(text: str) -> str:
    """Converts a string to a url-safe slug."""
    text = text.lower().strip()
    # Replace non-alphanumeric chars with hyphens
    text = re.sub(r'[^a-z0-9-]', '-', text)
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

@contextlib.contextmanager
def atomic_write(target_path: Path, mode: str = "w") -> Generator[Any, None, None]:
    """
    Atomic write pattern: write to temp, then rename.
    Enforces chmod 600 permission on the final file.
    """
    # Create a temp path alongside the target
    temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
    
    try:
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, mode) as f:
            yield f
            
            # Ensure flush to disk
            f.flush()
            os.fsync(f.fileno())

        # Apply secure permissions before moving
        os.chmod(temp_path, 0o600)
        
        # Atomic replace
        os.replace(temp_path, target_path)
        
    except Exception:
        # Cleanup temp file on failure
        if temp_path.exists():
            os.unlink(temp_path)
        raise
