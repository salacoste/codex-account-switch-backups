
# Auth0 Configuration for Codex
# TODO: Replace with actual Client ID once confirmed
CODEX_AUTH0_DOMAIN = "codex-platform.auth0.com" 
CODEX_CLIENT_ID = "YOUR_CLIENT_ID_HERE" 
CODEX_AUDIENCE = "https://api.codex.platform/"

# Auth Endpoints
DEVICE_CODE_URL = f"https://{CODEX_AUTH0_DOMAIN}/oauth/device/code"
TOKEN_URL = f"https://{CODEX_AUTH0_DOMAIN}/oauth/token"
USERINFO_URL = f"https://{CODEX_AUTH0_DOMAIN}/userinfo"

# Headers
DEFAULT_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded"
}
