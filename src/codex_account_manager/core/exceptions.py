class CodexError(Exception):
    """Base class for all Codex Account Manager errors."""
    def __init__(self, message: str, code: int = 1):
        self.message = message
        self.code = code
        super().__init__(self.message)

class AccountNotFoundError(CodexError):
    def __init__(self, account_name: str):
        super().__init__(f"Account '{account_name}' not found.", code=1)

class AccountExistsError(CodexError):
    def __init__(self, account_name: str):
        super().__init__(f"Account '{account_name}' already exists.", code=1)

class ConfigError(CodexError):
    """Raised when there is an issue loading or saving configuration."""
    pass
