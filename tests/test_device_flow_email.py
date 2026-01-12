import json
from typer.testing import CliRunner
from codex_account_manager.main import app
from unittest.mock import patch, MagicMock

runner = CliRunner()

def test_device_login_poll_fetches_email():
    """
    Verify that device-login-poll command calls get_user_info and includes email 
    in the JSON response when token check is successful.
    """
    # Mock DeviceAuth to intercept check_token and get_user_info
    with patch("codex_account_manager.commands.account.DeviceAuth") as MockDeviceAuth:
        mock_auth = MockDeviceAuth.return_value
        
        # Scenario: Token check succeeds
        mock_auth.check_token.return_value = {
            "status": "success",
            "tokens": {"access_token": "fake-access-token"}
        }
        
        # Scenario: User Info fetch succeeds
        mock_auth.get_user_info.return_value = {
            "email": "testuser@example.com",
            "sub": "auth0|123456"
        }
        
        # Invoke command
        result = runner.invoke(app, ["device-login-poll", "fake-device-code"])
        
        print(f"DEBUG STDOUT: '{result.stdout}'")
        print(f"DEBUG STDERR: '{result.stderr}'")

        # Assertions
        assert result.exit_code == 0, f"Exit code {result.exit_code}"
        
        data = json.loads(result.stdout)
        
        # Verify status and email
        assert data["status"] == "success"
        assert data["email"] == "testuser@example.com"
        assert data["tokens"]["access_token"] == "fake-access-token"
        
        # Verify get_user_info was called with correct token
        mock_auth.get_user_info.assert_called_once_with("fake-access-token")

def test_device_login_poll_handles_email_failure():
    """
    Verify that if fetching user info fails, the command still returns success 
    (token valid) but without the email field.
    """
    with patch("codex_account_manager.commands.account.DeviceAuth") as MockDeviceAuth:
        mock_auth = MockDeviceAuth.return_value
        
        mock_auth.check_token.return_value = {
            "status": "success",
            "tokens": {"access_token": "valid-token"}
        }
        
        # Simulate fetch failure
        from codex_account_manager.core.exceptions import CodexError
        mock_auth.get_user_info.side_effect = Exception("Network Error")
        
        result = runner.invoke(app, ["device-login-poll", "code"])
        
        print(f"DEBUG STDOUT (Fail Case): '{result.stdout}'")

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        
        assert data["status"] == "success"
        assert "email" not in data
