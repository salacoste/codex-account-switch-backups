import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from codex_account_manager.core.codex_api import CodexAPI
from codex_account_manager.commands.limits import app
from typer.testing import CliRunner
from codex_account_manager.config.models import Account, AccountType
from codex_account_manager.core.output import OutputManager

runner = CliRunner()

@pytest.mark.asyncio
async def test_get_usage_limits():
    """Test API client returns correct structure."""
    client = CodexAPI("mock-token")
    limits = await client.get_usage_limits()
    assert "limit_5h" in limits
    assert "limit_weekly" in limits
    assert limits["limit_5h"]["used"] == 42

def test_limits_command_show_json():
    """Test CLI output in JSON mode."""
    # Mock OutputManager
    mock_output = MagicMock(spec=OutputManager)
    
    # Create a root app to mount the limits command
    from typer import Typer
    root_app = Typer()
    root_app.add_typer(app, name="limits")
    
    with patch("codex_account_manager.commands.limits.ConfigManager") as MockConfig:
        mgr = MockConfig.return_value
        mgr.load_config.return_value.active_account = "test-acc"
        mgr.get_account.return_value = Account(
            name="test-acc",
            api_key="sk-test",
            type=AccountType.API_KEY,
            tags=[]
        )
        
        # We need to patch CodexAPI because the command instantiates it
        
        with patch("codex_account_manager.commands.limits.CodexAPI") as MockAPI:
            api_instance = MockAPI.return_value
            # Async mock
            api_instance.get_usage_limits = AsyncMock(return_value={
                "limit_5h": {"used": 10, "limit": 100},
                "limit_weekly": {"used": 50, "limit": 500}
            })
            
            # Use root_app invocation
            result = runner.invoke(root_app, ["limits", "show", "--json"], obj=mock_output)
            
            print("STDOUT:", result.stdout)
            print("EXIT CODE:", result.exit_code)
            
            assert result.exit_code == 0, f"Command failed with code {result.exit_code}. Output: {result.stdout}"
            # Verify print_json was called
            mock_output.print_json.assert_called_once()
            args, _ = mock_output.print_json.call_args
            assert args[0]["limit_5h"]["used"] == 10

def test_limits_command_show_table():
    """Test CLI output in Table mode."""
    mock_output = MagicMock(spec=OutputManager)
    # Mock console to check print
    mock_output.console = MagicMock()
    
    # Create a root app to mount the limits command, mimicking main.py
    # This prevents issues where 'ctx.obj' might be lost if invoking sub-app directly depending on Typer version
    from typer import Typer
    root_app = Typer()
    root_app.add_typer(app, name="limits")

    with patch("codex_account_manager.commands.limits.ConfigManager") as MockConfig:
        mgr = MockConfig.return_value
        mgr.load_config.return_value.active_account = "test-acc"
        mgr.get_account.return_value = Account(
             name="test-acc",
            api_key="sk-test",
            type=AccountType.API_KEY,
            tags=[]
        )
        
        with patch("codex_account_manager.commands.limits.CodexAPI") as MockAPI:
             api_instance = MockAPI.return_value
             api_instance.get_usage_limits = AsyncMock(return_value={
                "limit_5h": {"used": 10, "limit": 100},
                "limit_weekly": {"used": 50, "limit": 500}
            })
            
             result = runner.invoke(root_app, ["limits", "show"], obj=mock_output)
             print("STDOUT TABLE:", result.stdout)
             assert result.exit_code == 0, f"Command failed. Output: {result.stdout}"
             mock_output.console.print.assert_called()
