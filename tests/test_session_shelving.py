import pytest
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account, AccountType

@pytest.fixture
def mock_storage_root(tmp_path):
    """Creates a temporary home directory for testing."""
    root = tmp_path / ".codex-accounts"
    legacy_auth = tmp_path / ".codex" / "auth.json"
    legacy_auth.parent.mkdir(parents=True, exist_ok=True)
    return root, legacy_auth

def test_session_persistence(mock_storage_root, monkeypatch):
    """
    Verifies that sessions are shelved and restored correctly when switching accounts.
    """
    root, legacy_auth = mock_storage_root
    
    # Mock environment to map to our temp paths
    monkeypatch.setenv("HOME", str(root.parent))
    monkeypatch.setattr("codex_account_manager.config.manager.DEFAULT_CONFIG_ROOT", root)
    monkeypatch.setattr("codex_account_manager.config.manager.LEGACY_AUTH_FILE", legacy_auth)
    
    mgr = ConfigManager(root_path=root)
    
    # 1. Create two accounts
    acc1 = Account(name="personal", api_key="sk-1", type=AccountType.API_KEY)
    acc2 = Account(name="work", api_key="sk-2", type=AccountType.API_KEY)
    mgr.save_account(acc1)
    mgr.save_account(acc2)
    
    # 2. Start as 'personal'
    mgr.switch_account("personal")
    
    # 3. Simulate a Codex session file being created
    live_session_dir = legacy_auth.parent / "sessions"
    live_session_dir.mkdir(parents=True, exist_ok=True)
    session_file = live_session_dir / "session-123.json"
    session_file.write_text('{"id": "session-123", "context": "personal"}')
    
    assert session_file.exists(), "Session file should simulate existing in ~/.codex/sessions"
    
    # 4. Switch to 'work'
    mgr.switch_account("work")
    
    # ASSERTIONS:
    # - Live session dir should be cleaned or empty (since 'work' has no previous session)
    # - Personal session should be in shelving
    
    shelved_personal = root / "shelved_sessions" / "personal" / "session-123.json"
    assert shelved_personal.exists(), "Personal session should be shelved"
    assert shelved_personal.read_text() == '{"id": "session-123", "context": "personal"}'
    
    assert not session_file.exists(), "Live session should be cleared after switch"
    
    # 5. Simulate 'work' creating a session
    live_session_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists if logic cleared it
    work_session = live_session_dir / "work-session.json"
    work_session.write_text('{"id": "work-1", "context": "work"}')
    
    # 6. Switch back to 'personal'
    mgr.switch_account("personal")
    
    # ASSERTIONS
    # - Live session dir should now contain 'session-123.json' (Restored)
    # - 'work-session.json' should be in shelving for 'work'
    
    restored_personal = live_session_dir / "session-123.json"
    assert restored_personal.exists(), "Personal session should be restored"
    assert restored_personal.read_text() == '{"id": "session-123", "context": "personal"}'
    
    shelved_work = root / "shelved_sessions" / "work" / "work-session.json"
    assert shelved_work.exists(), "Work session should be shelved"
