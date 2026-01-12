import time
import httpx
from typing import Dict, Any
from codex_account_manager.config.constants import (
    CODEX_CLIENT_ID, 
    DEVICE_CODE_URL, 
    TOKEN_URL, 
    USERINFO_URL,
    DEFAULT_HEADERS
)
from codex_account_manager.core.exceptions import CodexError

class DeviceAuth:
    """
    Handles the OAuth 2.0 Device Authorization Flow.
    """
    def __init__(self):
        self.client_id = CODEX_CLIENT_ID
        self.http = httpx.Client(timeout=10.0)

    def initiate_flow(self) -> Dict[str, Any]:
        """
        Step 1: Request a device code.
        Returns: {device_code, user_code, verification_uri, interval, ...}
        """
        payload = {
            "client_id": self.client_id,
            "scope": "openid profile email offline_access", # Standart OIDC scopes
            "audience": "https://api.codex.platform/" # Optional, depending on provider
        }
        
        try:
            resp = self.http.post(DEVICE_CODE_URL, data=payload, headers=DEFAULT_HEADERS)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise CodexError(f"Failed to initiate authentication: {e}")

    def check_token(self, device_code: str) -> Dict[str, Any]:
        """
        Single check for token status.
        Returns: 
            - {"status": "success", "tokens": {...}}
            - {"status": "pending"} 
            - {"status": "slow_down", "interval_increment": 5}
            - Raises CodexError on fatal errors.
        """
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": self.client_id,
        }

        try:
            resp = self.http.post(TOKEN_URL, data=payload, headers=DEFAULT_HEADERS)
            data = resp.json()

            if resp.status_code == 200:
                return {"status": "success", "tokens": data}

            error = data.get("error")
            if error == "authorization_pending":
                return {"status": "pending"}
            elif error == "slow_down":
                return {"status": "slow_down", "interval_increment": 5}
            elif error == "expired_token":
                raise CodexError("Authentication timed out. Please try again.")
            elif error == "access_denied":
                raise CodexError("Authentication denied by user.")
            else:
                raise CodexError(f"Authentication failed: {error}")

        except httpx.RequestError as e:
            # Network error, treat as pending/retryable or raise?
            # For a single check, strictly speaking, it's an error, but let's re-raise 
            # so the caller decides to retry.
            raise CodexError(f"Network error during check: {e}")

    def poll_for_token(self, device_code: str, interval: int = 5) -> Dict[str, Any]:
        """
        Step 2: Poll for the access token until user approves or code expires.
        """
        # Polling loop
        while True:
            try:
                result = self.check_token(device_code)
                status = result["status"]
                
                if status == "success":
                    return result["tokens"]
                elif status == "slow_down":
                    interval += result.get("interval_increment", 5)
                
                # If pending or slow_down, wait
                time.sleep(interval)
                
            except CodexError as e:
                # Decide if fatal. 
                # 'Authentication timed out' -> Fatal (raised in check_token)
                # 'Network' -> maybe retry? check_token raises CodexError on network.
                # Compatibility with old behavior:
                if "Network error" in str(e):
                    time.sleep(interval)
                    continue
                raise e

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Step 3: Fetch user profile to identify the account (email).
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            resp = self.http.get(USERINFO_URL, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise CodexError(f"Failed to fetch user info: {e}")
