from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator

class AccountType(str, Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"

class Account(BaseModel):
    """
    Represents a single Codex account.
    Stores metadata and credentials.
    """
    name: str = Field(..., description="Unique slug for the account")
    email: Optional[str] = Field(None, description="Email associated with the account")
    
    # Credential Fields (One of these must be present)
    api_key: Optional[str] = Field(None, description="Codex API Key (for legacy auth)")
    
    type: AccountType = Field(default=AccountType.API_KEY, description="Type of authentication")
    
    created_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    tokens: Optional[Dict[str, Any]] = Field(None, description="OAuth tokens (access_token, etc)")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Custom environment variables to inject")
    tags: List[str] = Field(default_factory=list, description="List of user-defined tags")

    @model_validator(mode='after')
    def check_auth_presence(self) -> 'Account':
        # Must have at least one form of credential
        has_api_key = bool(self.api_key)
        has_tokens = bool(self.tokens)
        has_env_vars = bool(self.env_vars)
        
        if not (has_api_key or has_tokens or has_env_vars):
            raise ValueError("Account must have an api_key, tokens, or env_vars")
            
        # Infer type if not set? 
        # For now, explicit type or default API_KEY is fine, but maybe we add PROXY type?
        
        # Auto-detect type if not set explicitly (helpful for migration)
        if self.tokens and not self.api_key:
            self.type = AccountType.OAUTH
            
        return self

class Config(BaseModel):
    """
    Global configuration state.
    """
    active_account: Optional[str] = Field(None, description="Slug of the currently active account")
    
    # v3.0 Team Vaults Support
    mounts: Dict[str, str] = Field(default_factory=dict, description="Mounted vaults: slug -> path")
    team_keys: Dict[str, str] = Field(default_factory=dict, description="Encrypted team keys: slug -> cipher_text")
    
    created_at: datetime = Field(default_factory=datetime.now)
