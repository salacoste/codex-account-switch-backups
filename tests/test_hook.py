from typer.testing import CliRunner
from codex_account_manager.main import app
from unittest.mock import patch

runner = CliRunner()

def test_hook_found_in_cwd(tmp_path):
    """Verify hook detects file in current directory."""
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    
    (target_dir / ".codex-account").write_text("work-account")
    
    # Run with explicit path to avoid chdir in tests if possible, 
    # but command defaults to CWD. Using --path flag we implemented helps testing.
    result = runner.invoke(app, ["hook", "--path", str(target_dir)])
    
    if result.exit_code != 0:
        print(f"\nSTDOUT:\n{result.stdout}")
        
    assert result.exit_code == 0
    assert "work-account" in result.stdout.strip()

def test_hook_found_in_parent(tmp_path):
    """Verify hook detects file in parent directory."""
    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / ".codex-account").write_text("root-account")
    
    child = parent / "child" / "grandchild"
    child.mkdir(parents=True)
    
    result = runner.invoke(app, ["hook", "--path", str(child)])
    
    assert result.exit_code == 0
    assert "root-account" in result.stdout.strip()

def test_hook_not_found(tmp_path):
    """Verify hook returns exit code 1 if not found."""
    # Ensure no .codex-account in tmp_path or parents (pytests tmp_path usually safe)
    result = runner.invoke(app, ["hook", "--path", str(tmp_path)])
    
    assert result.exit_code == 1
    assert result.stdout == ""

def test_hook_empty_file(tmp_path):
    """Verify empty file is treated as not found."""
    p = tmp_path / ".codex-account"
    p.write_text("")
    
    result = runner.invoke(app, ["hook", "--path", str(tmp_path)])
    
    # Our logic says exit 1 if not found OR empty
    assert result.exit_code == 1


def test_hook_read_error(tmp_path):
    """Verify exception during read is treated as not found."""
    p = tmp_path / ".codex-account"
    p.write_text("ok")
    
    with patch("codex_account_manager.commands.hook.find_local_config") as mock_find:
        # Mock returned path behaves like Path but raises on read_text
        mock_path = patch("pathlib.Path").start()
        mock_path.read_text.side_effect = Exception("Read fail")
        
        mock_find.return_value = mock_path
        
        result = runner.invoke(app, ["hook", "--path", str(tmp_path)])
        
        assert result.exit_code == 1
        mock_path.read_text.assert_called_once()
        patch.stopall()
