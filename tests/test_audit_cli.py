from unittest.mock import patch
from typer.testing import CliRunner
from codex_account_manager.main import app
from codex_account_manager.core.audit import AuditManager

runner = CliRunner()

def test_audit_cli_view(tmp_path):
    """Verify audit cli shows events."""
    # 1. Seed events
    audit = AuditManager(root_path=tmp_path)
    audit.log_event("login", "user1")
    audit.log_event("delete", "user2")
    
    # 2. Run CLI (need to mock AuditManager used by CLI to point to tmp_path)
    # The CLI instantiates AuditManager() with default path (home).
    # We must patch it.
    
    with patch("codex_account_manager.commands.audit.AuditManager") as MockAuditCls:
        # Return our pre-seeded audit instance or mock one that returns events
        # Easier to mock the instance methods
        mock_instance = MockAuditCls.return_value
        mock_instance.get_events.return_value = [
            {"timestamp": "2024-01-01T12:00:00", "event": "delete", "account": "user2", "details": {}},
            {"timestamp": "2024-01-01T11:00:00", "event": "login", "account": "user1", "details": {}}
        ]
        
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        output = f"{result.stdout} {result.stderr}"
        assert "user1" in output
        assert "user2" in output
        assert "delete" in output

def test_audit_cli_filter(tmp_path):
    """Verify filtering."""
    with patch("codex_account_manager.commands.audit.AuditManager") as MockAuditCls:
        mock_instance = MockAuditCls.return_value
        mock_instance.get_events.return_value = [
            {"timestamp": "2024-01-01T12:00:00", "event": "delete", "account": "user2", "details": {}},
            {"timestamp": "2024-01-01T11:00:00", "event": "login", "account": "user1", "details": {}}
        ]
        
        # Filter by user1
        result = runner.invoke(app, ["audit", "--account", "user1"])
        assert result.exit_code == 0
        output = f"{result.stdout} {result.stderr}"
        assert "user1" in output
        assert "user2" not in output

def test_audit_no_events(tmp_path):
    """Verify empty state."""
    with patch("codex_account_manager.commands.audit.AuditManager") as MockAuditCls:
        MockAuditCls.return_value.get_events.return_value = []
        
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "No audit events found" in f"{result.stdout} {result.stderr}"

def test_audit_filter_no_match(tmp_path):
    """Verify filter yielding no results."""
    with patch("codex_account_manager.commands.audit.AuditManager") as MockAuditCls:
        mock_instance = MockAuditCls.return_value
        mock_instance.get_events.return_value = [
            {"timestamp": "2024-01-01T12:00:00", "event": "login", "account": "u1", "details": {}}
        ]
        
        result = runner.invoke(app, ["audit", "--account", "u2"])
        assert result.exit_code == 0
        assert "No events match filter" in f"{result.stdout} {result.stderr}"

def test_audit_event_styles_and_bad_ts(tmp_path):
    """Verify styling for different events and bad timestamp handling."""
    with patch("codex_account_manager.commands.audit.AuditManager") as MockAuditCls:
        mock_instance = MockAuditCls.return_value
        mock_instance.get_events.return_value = [
            {"timestamp": "bad-ts", "event": "modify", "account": "u1", "details": {}},
            {"timestamp": "2024-01-01T10:00:00", "event": "accessDecrypted", "account": "u2", "details": {}},
            {"timestamp": "2024-01-01T11:00:00", "event": "delete", "account": "u3", "details": {}},
        ]
        
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        output = f"{result.stdout} {result.stderr}"
        
        assert "bad-ts" in output # fallback used
        # Check Rich markup presence if possible, or just content
        assert "modify" in output
        assert "accessDecrypted" in output
        assert "delete" in output
