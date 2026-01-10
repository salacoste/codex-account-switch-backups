import pytest
from unittest.mock import MagicMock, patch
from codex_account_manager.commands.auth import DeviceAuth
from codex_account_manager.core.exceptions import CodexError

@pytest.fixture
def mock_http():
    with patch("httpx.Client") as mock:
        yield mock.return_value

def test_initiate_flow_success(mock_http):
    auth = DeviceAuth()
    
    # Mock Response object
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "device_code": "dcode",
        "user_code": "ucode",
        "verification_uri": "http://verify",
        "interval": 5
    }
    mock_http.post.return_value = mock_resp

    result = auth.initiate_flow()
    assert result["device_code"] == "dcode"
    
def test_poll_for_token_success(mock_http):
    auth = DeviceAuth()
    
    # Response 1: Pending (403 or 400 usually, let's say 400 for safety)
    resp1 = MagicMock()
    resp1.status_code = 400
    resp1.json.return_value = {"error": "authorization_pending"}
    
    # Response 2: Success
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {"access_token": "secret_token"}
    
    mock_http.post.side_effect = [resp1, resp2]
    
    with patch("time.sleep") as mock_sleep: # Don't actually sleep
        token = auth.poll_for_token("dcode", interval=1)
        
    assert token["access_token"] == "secret_token"
    assert mock_sleep.call_count == 1

def test_poll_for_token_timeout(mock_http):
    auth = DeviceAuth()
    
    # Response: Expired
    resp = MagicMock()
    resp.status_code = 400
    resp.json.return_value = {"error": "expired_token"}
    mock_http.post.return_value = resp
    
    with pytest.raises(CodexError, match="timed out"):
        with patch("time.sleep"):
            auth.poll_for_token("dcode")

def test_get_user_info_success(mock_http):
    auth = DeviceAuth()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"email": "test@example.com"}
    mock_http.get.return_value = mock_resp
    
    info = auth.get_user_info("token")
    assert info["email"] == "test@example.com"

