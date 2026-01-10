from typer.testing import CliRunner
from unittest.mock import patch
from codex_account_manager.main import app
from codex_account_manager.core.exceptions import CodexError
from codex_account_manager.config.models import Account

runner = CliRunner()

@patch("codex_account_manager.commands.tui.questionary")
@patch("codex_account_manager.commands.tui.ConfigManager")
def test_tui_success(MockMgr, MockQuestionary, mock_config):
    """Verify TUI lists accounts and switches on selection."""
    # Setup Accounts
    mgr = MockMgr.return_value
    mgr.list_accounts.return_value = [
        Account(name="acc1", email="a@b.com", api_key="k1"),
        Account(name="acc2", email="c@d.com", api_key="k2")
    ]
    
    # Setup Selection Mock
    # questionary.select(...).ask() -> "acc2"
    select_mock = MockQuestionary.select.return_value
    select_mock.ask.return_value = "acc2"
    
    # Run
    result = runner.invoke(app, ["tui"])
    
    combined = f"{result.stdout} {result.stderr or ''}"
    assert result.exit_code == 0
    assert "Switched to account 'acc2'" in combined
    
    # Verify switch called
    mgr.switch_account.assert_called_with("acc2")
    
    # Verify choices passed to questionary
    args, kwargs = MockQuestionary.select.call_args
    choices = kwargs.get('choices', [])
    assert "acc1" in choices
    assert "acc2" in choices

@patch("codex_account_manager.commands.tui.questionary")
@patch("codex_account_manager.commands.tui.ConfigManager")
def test_tui_no_accounts(MockMgr, MockQuestionary, mock_config):
    """Verify TUI handles empty account list gracefully."""
    mgr = MockMgr.return_value
    mgr.list_accounts.return_value = []
    
    result = runner.invoke(app, ["tui"])
    
    combined = f"{result.stdout} {result.stderr or ''}"
    assert result.exit_code == 0
    assert "No accounts found" in combined
    
    # Questionary should NOT be called
    MockQuestionary.select.assert_not_called()

@patch("codex_account_manager.commands.tui.questionary")
@patch("codex_account_manager.commands.tui.ConfigManager")
def test_tui_cancellation(MockMgr, MockQuestionary, mock_config):
    """Verify TUI handles cancellation (None return)."""
    mgr = MockMgr.return_value
    mgr.list_accounts.return_value = [Account(name="a", email="e", api_key="k")]
    
    # Simulate user cancelling (some backends return None)
    select_mock = MockQuestionary.select.return_value
    select_mock.ask.return_value = None
    
    result = runner.invoke(app, ["tui"])
    
    assert result.exit_code == 0
    mgr.switch_account.assert_not_called()


@patch("codex_account_manager.commands.tui.questionary")
@patch("codex_account_manager.commands.tui.ConfigManager")
def test_tui_keyboard_interrupt(MockMgr, MockQuestionary, mock_config):
    """Verify TUI handles Ctrl+C."""
    mgr = MockMgr.return_value
    mgr.list_accounts.return_value = [Account(name="a", email="e", api_key="k")]
    
    MockQuestionary.select.return_value.ask.side_effect = KeyboardInterrupt()
    
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 0
    assert "Cancelled" in f"{result.stdout} {result.stderr}"

@patch("codex_account_manager.commands.tui.questionary")
@patch("codex_account_manager.commands.tui.ConfigManager")
def test_tui_codex_error(MockMgr, MockQuestionary, mock_config):
    """Verify cleanup on CodexError."""
    mgr = MockMgr.return_value
    mgr.list_accounts.return_value = [Account(name="a", email="e", api_key="k")]
    
    MockQuestionary.select.return_value.ask.return_value = "a"
    mgr.switch_account.side_effect = CodexError("SwitchFail")
    
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 1
    assert "SwitchFail" in f"{result.stdout} {result.stderr}"
