import pytest
import json
from codex_account_manager.ingest.legacy import LegacyIngestor
from codex_account_manager.core.exceptions import CodexError

@pytest.fixture
def legacy_root(tmp_path):
    """Creates a mock legacy project structure."""
    root = tmp_path / "old-project"
    root.mkdir()
    (root / "accounts").mkdir()
    return root

def create_mock_account(root, slug, api_key_field="api_key", api_key_val="sk-test", has_meta=True):
    acc_dir = root / "accounts" / slug
    acc_dir.mkdir(parents=True, exist_ok=True)
    
    if has_meta:
        (acc_dir / "account.json").write_text("{}")
    
    # Create backup structure
    backups = acc_dir / "backups"
    backups.mkdir(exist_ok=True)
    
    auth_data = {"email": f"{slug}@test.com"}
    if api_key_val is not None:
        auth_data[api_key_field] = api_key_val
    
    # Create a couple of backups, we want the latest
    (backups / "backup-20240101.auth.json").write_text(json.dumps(auth_data))
    (backups / "backup-20250101.auth.json").write_text(json.dumps(auth_data))
    
    return acc_dir

def create_mock_account_v2(root, slug, auth_data, has_meta=True):
    """Refactored helper for flexible auth data"""
    acc_dir = root / "accounts" / slug
    acc_dir.mkdir(parents=True, exist_ok=True)
    
    if has_meta:
        (acc_dir / "account.json").write_text("{}")
    
    backups = acc_dir / "backups"
    backups.mkdir(exist_ok=True)
    
    (backups / "backup-20250101.auth.json").write_text(json.dumps(auth_data))
    return acc_dir

def test_scan_invalid_path(tmp_path):
    ingestor = LegacyIngestor()
    with pytest.raises(CodexError):
        list(ingestor.scan(tmp_path / "non-existent"))

def test_scan_not_a_project(tmp_path):
    # Missing 'accounts' dir
    ingestor = LegacyIngestor()
    with pytest.raises(CodexError, match="missing 'accounts/' dir"):
        list(ingestor.scan(tmp_path))

def test_scan_valid_accounts(legacy_root):
    # Standard account
    create_mock_account(legacy_root, "standard", "api_key", "sk-std")
    
    # Legacy OpenAI key account
    create_mock_account(legacy_root, "openai", "OPENAI_API_KEY", "sk-openai")
    
    ingestor = LegacyIngestor()
    results = list(ingestor.scan(legacy_root))
    
    # Sort by name to be sure
    results.sort(key=lambda x: x.name)
    
    assert len(results) == 2
    assert results[0].name == "openai"
    assert results[0].api_key == "sk-openai"
    assert results[1].name == "standard" 
    assert results[1].api_key == "sk-std"
    assert results[1].name == "standard" 
    assert results[1].api_key == "sk-std"

def test_scan_oauth_account(legacy_root):
    """Story 8.2: Verify account with tokens but no API key is accepted."""
    tokens = {"access_token": "abc", "refresh_token": "def"}
    create_mock_account_v2(legacy_root, "korean-oauth", 
                         {"tokens": tokens, "api_key": None, "email": "oauth@test.com"})
    
    ingestor = LegacyIngestor()
    results = list(ingestor.scan(legacy_root))
    
    assert len(results) == 1
    assert results[0].name == "korean-oauth"
    assert results[0].api_key is None
    assert results[0].tokens == tokens

def test_scan_ignore_invalid(legacy_root):
    # No metadata file -> Ignored
    create_mock_account(legacy_root, "no-meta", has_meta=False)
    
    # No API Key in auth -> Ignored
    create_mock_account(legacy_root, "no-key", "api_key", "")
    
    ingestor = LegacyIngestor()
    results = list(ingestor.scan(legacy_root))
    
    assert len(results) == 0

def test_scan_finds_auth_in_root_fallback(legacy_root):
    """Test fallback to auth.json if no backups exist."""
    slug = "fallback"
    acc_dir = legacy_root / "accounts" / slug
    acc_dir.mkdir(parents=True)
    (acc_dir / "account.json").write_text("{}")
    
    # Direct auth.json
    (acc_dir / "auth.json").write_text(json.dumps({"api_key": "sk-fallback"}))
    
    ingestor = LegacyIngestor()
    results = list(ingestor.scan(legacy_root))
    
    assert len(results) == 1
    assert results[0].api_key == "sk-fallback"

def test_scan_ignores_files(legacy_root):
    """Verify files in accounts/ are ignored (must be dirs)."""
    (legacy_root / "accounts" / "somefile.txt").write_text("ignore")
    
    ingestor = LegacyIngestor()
    results = list(ingestor.scan(legacy_root))
    assert len(results) == 0

def test_scan_corrupt_auth(legacy_root):
    """Verify corrupted auth files are skipped."""
    acc_dir = legacy_root / "accounts" / "corrupt"
    acc_dir.mkdir(parents=True)
    (acc_dir / "account.json").write_text("{}")
    
    # Invalid JSON
    (acc_dir / "auth.json").write_text("{badjson")
    
    ingestor = LegacyIngestor()
    results = list(ingestor.scan(legacy_root))
    assert len(results) == 0
