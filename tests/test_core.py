from codex_account_manager.core.output import OutputManager
from codex_account_manager.core.exceptions import CodexError, AccountNotFoundError

def test_output_manager_clean_pipe(capsys):
    """Verify OutputManager separates data (stdout) from logs (stderr)."""
    out = OutputManager()
    
    # 1. Log something (should go to stderr)
    out.log("This is a log")
    out.success("This is success")
    out.error("This is error")
    
    captured = capsys.readouterr()
    assert "This is a log" in captured.err
    assert "This is success" in captured.err
    assert "This is error" in captured.err
    assert captured.out == ""  # Stdout should be clean
    
    # 2. Print JSON (should go to stdout)
    out.print_json({"key": "value"})
    
    captured = capsys.readouterr()
    import json
    data = json.loads(captured.out)
    assert data == {"key": "value"}
    assert captured.err == "" # Stderr should be clean during data output

def test_codex_error_base():
    """Verify CodexError carries code and message."""
    err = CodexError("Something went wrong", code=5)
    assert str(err) == "Something went wrong"
    assert err.code == 5

def test_custom_exception_inheritance():
    """Verify specific exceptions inherit correctly."""
    err = AccountNotFoundError("magic-account")
    assert isinstance(err, CodexError)
    assert "magic-account" in err.message
    assert err.code == 1
