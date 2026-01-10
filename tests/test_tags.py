from typer.testing import CliRunner
from unittest.mock import patch
from codex_account_manager.main import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account

runner = CliRunner()

def test_add_with_tags(mock_config):
    """Verify adding account with --tag flag."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        result = runner.invoke(app, [
            "add", "tagged-acc", 
            "--email", "t@t.com", 
            "--api-key", "k", 
            "--tag", "work", 
            "--tag", "prod"
        ])
        
        assert result.exit_code == 0
        
    cm = ConfigManager(root_path=mock_config)
    acc = cm.get_account("tagged-acc")
    assert "work" in acc.tags
    assert "prod" in acc.tags

def test_list_filter_tags(mock_config):
    """Verify list --tag filtering."""
    cm = ConfigManager(root_path=mock_config)
    cm.save_account(Account(name="work-acc", email="w", api_key="k", tags=["work"]))
    cm.save_account(Account(name="personal-acc", email="p", api_key="k", tags=["personal"]))
    cm.save_account(Account(name="mixed-acc", email="m", api_key="k", tags=["work", "legacy"]))
    
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=mock_config)
        
        # Filter 'work'
        result = runner.invoke(app, ["list", "--tag", "work"])
        assert result.exit_code == 0
        combined = f"{result.stdout} {result.stderr or ''}"
        assert "work-acc" in combined
        assert "mixed-acc" in combined
        assert "personal-acc" not in combined
        
        # Filter 'personal'
        result = runner.invoke(app, ["list", "--tag", "personal"])
        assert result.exit_code == 0
        combined = f"{result.stdout} {result.stderr or ''}"
        assert "personal-acc" in combined
        assert "work-acc" not in combined

        # Filter 'missing'
        result = runner.invoke(app, ["list", "--tag", "missing"])
        assert result.exit_code == 0
        # Should show empty table with no rows provided by 'accounts'
        # Or empty table output
        combined = f"{result.stdout} {result.stderr or ''}"
        assert "work-acc" not in combined
