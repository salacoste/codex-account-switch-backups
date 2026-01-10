import os
from codex_account_manager.core.utils import atomic_write

def test_atomic_write_permissions(tmp_path):
    target = tmp_path / "secure.txt"
    
    with atomic_write(target) as f:
        f.write("secret")
        
    assert target.exists()
    assert target.read_text() == "secret"
    
    # Check permissions logic
    # stat.st_mode includes file type bits, so we mask with 0o777
    mode = os.stat(target).st_mode & 0o777
    assert mode == 0o600, f"Expected 0600, got {oct(mode)}"
