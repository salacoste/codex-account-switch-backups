import pytest
from codex_account_manager.config.models import Account, AccountType

def test_legacy_api_key_account():
    """Verify standard API key account creation works."""
    acc = Account(name="legacy-user", api_key="sk-1234")
    assert acc.api_key == "sk-1234"
    assert acc.tokens is None
    assert acc.type == AccountType.API_KEY

def test_oauth_account_creation():
    """Verify OAuth account creation works with tokens."""
    token_data = {
        "access_token": "abc",
        "refresh_token": "def",
        "expires_in": 3600
    }
    acc = Account(name="oauth-user", tokens=token_data)
    
    assert acc.api_key is None
    assert acc.tokens == token_data
    # Should auto-detect OAUTH type
    assert acc.type == AccountType.OAUTH

def test_invalid_empty_account():
    """Verify account requires at least one credential."""
    with pytest.raises(ValueError) as excinfo:
        Account(name="invalid")
    
    assert "api_key, tokens, or env_vars" in str(excinfo.value)

def test_both_types_defaults():
    """Verify explicit override of type."""
    acc = Account(
        name="hybrid", 
        api_key="sk-123", 
        tokens={"t": 1},
        type=AccountType.OAUTH
    )
    assert acc.type == AccountType.OAUTH
