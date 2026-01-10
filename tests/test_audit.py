import json
from unittest.mock import patch
from pathlib import Path
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account
from codex_account_manager.core.audit import AuditManager

def test_audit_log_creation(tmp_path):
    """Verify audit log is created and written to."""
    audit = AuditManager(root_path=tmp_path)
    audit.log_event("test_event", "test_account", {"foo": "bar"})
    
    log_file = tmp_path / "audit.log"
    assert log_file.exists()
    
    content = log_file.read_text()
    entry = json.loads(content)
    
    assert entry["event"] == "test_event"
    assert entry["account"] == "test_account"
    assert entry["details"]["foo"] == "bar"

def test_manager_logs_access(tmp_path):
    """Verify ConfigManager logs access on get_account."""
    mgr = ConfigManager(root_path=tmp_path)
    mgr.save_account(Account(name="audit-test", api_key="k"))
    
    # 1. Trigger Login (get_account with decrypted=True default is False for get_account? No, usually True in commands)
    # Let's check get_account signature. It has decrypted arg.
    # We didn't change default but commands usually ask for it.
    
    # Explicitly call with decrypted=True
    mgr.get_account("audit-test", decrypted=True)
    
    # Check Log
    log_file = tmp_path / "audit.log"
    lines = log_file.read_text().strip().split('\n')
    
    # Expect 2 events: modify (save), access (get)
    assert len(lines) >= 2
    
    save_event = json.loads(lines[0])
    assert save_event["event"] == "modify"
    
    access_event = json.loads(lines[-1])
    assert access_event["event"] == "access"
    assert access_event["details"]["decrypted"] is True

def test_audit_rotation_limit(tmp_path):
    """Verify get_events limit."""
    audit = AuditManager(root_path=tmp_path)
    for i in range(10):
        audit.log_event("event", f"acc-{i}")
        
    events = audit.get_events(limit=5)
    assert len(events) == 5
    events = audit.get_events(limit=5)
    assert len(events) == 5
    assert events[0]["account"] == "acc-9" # Newest first (reversed)

def test_audit_default_init():
    """Verify default path."""
    with patch("pathlib.Path.home") as mock_home, \
         patch("codex_account_manager.core.audit.AuditManager._ensure_dir"):
        mock_home.return_value = Path("/mock/home")
        audit = AuditManager()
        assert audit.log_file == Path("/mock/home/.codex-accounts/audit.log")

def test_ensure_dir_creation(tmp_path):
    """Verify directory creation."""
    log_dir = tmp_path / "deep" / "nested"
    _audit = AuditManager(root_path=log_dir)
    assert log_dir.exists()

def test_log_write_failure(tmp_path):
    """Verify write failure is silent."""
    audit = AuditManager(root_path=tmp_path)
    with patch("builtins.open", side_effect=OSError("Write fail")):
        # Should not raise
        audit.log_event("evt", "acc")

def test_get_events_missing_file(tmp_path):
    """Verify missing file returns empty."""
    audit = AuditManager(root_path=tmp_path)
    # Don't log anything so file doesn't start existing (init only creates dir)
    # Actually init creates dir, not file.
    assert audit.get_events() == []

def test_get_events_read_failure(tmp_path):
    """Verify read failure returns empty."""
    audit = AuditManager(root_path=tmp_path)
    audit.log_event("a", "b") # create file
    
    with patch("builtins.open", side_effect=OSError("Read fail")):
        assert audit.get_events() == []

def test_get_events_corrupt_data(tmp_path):
    """Verify corrupt lines are skipped."""
    audit = AuditManager(root_path=tmp_path)
    log_file = tmp_path / "audit.log"
    log_file.write_text('{"valid": 1}\n{corrupt\n{"valid": 2}\n')
    
    events = audit.get_events()
    assert len(events) == 2
    assert events[0]["valid"] == 2 # Newest first (reversed)
    assert events[1]["valid"] == 1
