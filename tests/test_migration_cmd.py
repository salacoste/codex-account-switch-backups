from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from codex_account_manager.commands.account import app
from codex_account_manager.config.manager import ConfigManager
from codex_account_manager.config.models import Account


runner = CliRunner()

def test_encrypt_all_migration(tmp_path):
    """Verify encrypt-all converts legacy to encrypted."""
    # Setup: Create legacy account manually
    acc_dir = tmp_path / "accounts" / "legacy-user"
    acc_dir.mkdir(parents=True)
    legacy_file = acc_dir / "auth.json"
    legacy_file.write_text(Account(name="legacy-user", api_key="sk-old").model_dump_json())
    
    # Run command
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        # We need a real manager logic to perform encryption
        real_manager = ConfigManager(root_path=tmp_path)
        MockMgr.return_value = real_manager
        
        # Mock OutputManager to verify calls
        mock_out = MagicMock()
        # We need console.status to be a context manager
        mock_out.console.status.return_value.__enter__.return_value = None
        
        result = runner.invoke(app, ["encrypt-all", "-y"], obj=mock_out)
        
        assert result.exit_code == 0
        
        # Verify success message was logged
        # match string "Successfully encrypted 1/1"
        mock_out.success.assert_called()
        args = mock_out.success.call_args[0][0]
        assert "Successfully encrypted 1/1" in args
        
    # Verify file system state
    auth_enc = acc_dir / "auth.enc"
    assert auth_enc.exists()
    assert not legacy_file.exists()
    
    # Verify content is encrypted
    assert b"sk-old" not in auth_enc.read_bytes()

def test_encrypt_all_empty(tmp_path):
    """Verify behavior with no accounts."""
    with patch("codex_account_manager.commands.account.ConfigManager") as MockMgr:
        MockMgr.return_value = ConfigManager(root_path=tmp_path)
        
        mock_out = MagicMock()
        
        runner.invoke(app, ["encrypt-all"], obj=mock_out)
        
        mock_out.warn.assert_called_with("No accounts found to encrypt.")
