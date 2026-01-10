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

    def poll_for_token(self, device_code: str, interval: int = 5) -> Dict[str, Any]:
        """
        Step 2: Poll for the access token until user approves or code expires.
        """
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": self.client_id,
        }

        # Polling loop
        while True:
            try:
                resp = self.http.post(TOKEN_URL, data=payload, headers=DEFAULT_HEADERS)
                data = resp.json()

                if resp.status_code == 200:
                    return data # Success!

                error = data.get("error")
                if error == "authorization_pending":
                    pass # Keep waiting
                elif error == "slow_down":
                    interval += 5 # OAUTH spec says increase interval
                elif error == "expired_token":
                    raise CodexError("Authentication timed out. Please try again.")
                elif error == "access_denied":
                    raise CodexError("Authentication denied by user.")
                else:
                    raise CodexError(f"Authentication failed: {error}")

            except httpx.RequestError:
                # Network glitch? Wait and retry
                pass

            time.sleep(interval)

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
