from typer.testing import CliRunner
from unittest.mock import patch
from codex_account_manager.main import app
from codex_account_manager.config.models import Account
from codex_account_manager.core.exceptions import AccountNotFoundError

runner = CliRunner()

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_success(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify successful migration of new accounts."""
    # Create valid source dir
    source = tmp_path / "legacy_source"
    source.mkdir()

    # Setup mocks
    mgr_instance = MockMgr.return_value
    mgr_instance.get_account.side_effect = AccountNotFoundError("new") # Does not exist
    
    ingest_instance = MockIngest.return_value
    ingest_instance.scan.return_value = [
        Account(name="migrated-acc", email="m@test.com", api_key="sk-m")
    ]
    
    # Run
    result = runner.invoke(app, ["migrate", "--from", str(source)])
    
    combined = f"{result.stdout} {result.stderr or ''}"
    assert result.exit_code == 0
    assert "Imported 'migrated-acc'" in combined
    assert "Migration complete" in combined
    
    # Verify save called
    mgr_instance.save_account.assert_called_once()
    saved_acc = mgr_instance.save_account.call_args[0][0]
    assert saved_acc.name == "migrated-acc"

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_skip_duplicate(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify duplicates are skipped by default."""
    source = tmp_path / "legacy_source"
    source.mkdir()

    mgr_instance = MockMgr.return_value
    # account exists
    mgr_instance.get_account.return_value = Account(name="dup", email="d", api_key="k")
    
    ingest_instance = MockIngest.return_value
    ingest_instance.scan.return_value = [
        Account(name="dup", email="migrating@test.com", api_key="sk-new")
    ]
    
    result = runner.invoke(app, ["migrate", "--from", str(source)])
    
    combined = f"{result.stdout} {result.stderr or ''}"
    assert result.exit_code == 0
    assert "Skipping 'dup'" in combined
    
    # Save NOT called
    mgr_instance.save_account.assert_not_called()

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_force_overwrite(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify duplicates overwritten with --force."""
    source = tmp_path / "legacy_source"
    source.mkdir()

    mgr_instance = MockMgr.return_value
    mgr_instance.get_account.return_value = Account(name="dup", email="old", api_key="old")
    
    ingest_instance = MockIngest.return_value
    ingest_instance.scan.return_value = [
        Account(name="dup", email="new@test.com", api_key="new")
    ]
    
    result = runner.invoke(app, ["migrate", "--from", str(source), "--force"])
    
    combined = f"{result.stdout} {result.stderr or ''}"
    assert result.exit_code == 0
    assert "Overwriting" in combined
    assert "Imported 'dup'" in combined
    
    mgr_instance.save_account.assert_called_once()

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_dry_run(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify dry run saves nothing."""
    source = tmp_path / "legacy_source"
    source.mkdir()

    mgr_instance = MockMgr.return_value
    mgr_instance.get_account.side_effect = AccountNotFoundError("new")
    
    ingest_instance = MockIngest.return_value
    ingest_instance.scan.return_value = [
        Account(name="dry check", email="d", api_key="k")
    ]
    
    result = runner.invoke(app, ["migrate", "--from", str(source), "--dry-run"])
    
    combined = f"{result.stdout} {result.stderr or ''}"
    assert result.exit_code == 0
    assert "Dry Run" in combined
    
    mgr_instance.save_account.assert_not_called()

from codex_account_manager.core.exceptions import CodexError

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_default_path(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify default source path."""
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        # We need mock scan to fail or succeed, but not crash on path existence?
        # Default path is tmp_path / "old-project"
        expected = tmp_path / "old-project"
        expected.mkdir()
        
        MockIngest.return_value.scan.return_value = []
        
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code == 0
        combined = f"{result.stdout} {result.stderr or ''}"
        assert "Scanning" in combined
        MockIngest.return_value.scan.assert_called_with(expected)

def test_migrate_source_missing(tmp_path):
    """Verify missing source error."""
    missing = tmp_path / "ghost"
    result = runner.invoke(app, ["migrate", "--from", str(missing)])
    assert result.exit_code == 1
    assert "does not exist" in  f"{result.stdout} {result.stderr}"

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_save_error(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify save error handling."""
    source = tmp_path / "src"
    source.mkdir()
    
    MockMgr.return_value.scan.return_value = [] # unused
    mgr = MockMgr.return_value
    mgr.get_account.side_effect = AccountNotFoundError("new")
    mgr.save_account.side_effect = CodexError("SaveFail")
    
    MockIngest.return_value.scan.return_value = [Account(name="a", api_key="k")]
    
    result = runner.invoke(app, ["migrate", "--from", str(source)])
    assert result.exit_code == 0 # Warning only, continues
    assert "Failed to save 'a'" in f"{result.stdout} {result.stderr}"

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_empty_scan(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify empty scan results."""
    source = tmp_path / "src"
    source.mkdir()
    MockIngest.return_value.scan.return_value = []
    
    result = runner.invoke(app, ["migrate", "--from", str(source)])
    assert result.exit_code == 0
    assert "No accounts found" in f"{result.stdout} {result.stderr}"

@patch("codex_account_manager.commands.migrate.LegacyIngestor")
@patch("codex_account_manager.commands.migrate.ConfigManager")
def test_migrate_scan_fatal_error(MockMgr, MockIngest, mock_config, tmp_path):
    """Verify fatal scan error."""
    source = tmp_path / "src"
    source.mkdir()
    MockIngest.return_value.scan.side_effect = CodexError("ScanFail")
    
    result = runner.invoke(app, ["migrate", "--from", str(source)])
    assert result.exit_code == 1
    assert "ScanFail" in f"{result.stdout} {result.stderr}"
