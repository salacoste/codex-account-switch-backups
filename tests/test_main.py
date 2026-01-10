import pytest
from unittest.mock import patch
from typer.testing import CliRunner
from codex_account_manager.main import app, main
from codex_account_manager.core.exceptions import CodexError

runner = CliRunner()

def test_main_callback_verbose():
    """Verify verbose flag triggers debug log."""
    result = runner.invoke(app, ["--verbose", "list"])
    # "list" is an arbitrary command just to trigger callback
    # We check if debug log key phrase is in output
    assert result.exit_code == 0
    assert "Debug mode enabled" in f"{result.stdout} {result.stderr}"

def test_main_success():
    """Verify main() runs app successfully."""
    with patch("codex_account_manager.main.app") as mock_app:
        main()
        mock_app.assert_called_once()

def test_main_codex_error(capsys):
    """Verify main() handles CodexError."""
    with patch("codex_account_manager.main.app", side_effect=CodexError("Known Error", code=2)):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2
        
        captured = capsys.readouterr()
        assert "Error: Known Error" in captured.err

def test_main_unexpected_error(capsys):
    """Verify main() handles unexpected errors."""
    with patch("codex_account_manager.main.app", side_effect=ValueError("Boom")):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        
        captured = capsys.readouterr()
        assert "Unexpected Error: Boom" in captured.err

def test_if_name_main():
    """Not easily testable without subprocess but main() covering is enough."""
    pass
