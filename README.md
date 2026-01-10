# Codex Account Manager

A secure CLI tool for managing multiple Codex accounts and safely switching authentication contexts.  
Developed to separate production credentials from test environments and simplify multi-account workflows.

## 🚀 Features

*   **Secure Storage**: Credentials stored encrypted (AES-256) with `chmod 600`.
*   **Universal Proxy**: Inject credentials into any command (`codex-account run`) without exports.
*   **Git Sync**: Synchronize your vault across machines using a private Git repo.
*   **Context Awareness**: Auto-switch identities based on directory or session.
*   **Audit Logging**: Track every key access for security and compliance.
*   **Legacy Migration**: Auto-import accounts from old project structures.
*   **Rich Output**: Beautiful terminal output with masking for sensitive data.

📖 **[Read the Full User Guide](docs/USER_GUIDE.md)** for detailed instructions.

## 📦 Installation

```bash
# Clone the repository
git clone <repo-url>
cd codex-account-manager

# Install with Poetry
poetry install

# Activate shell
poetry shell
```

## 🛠️ Usage

### 1. Initialization
First, initialize the secure storage directory (`~/.codex-accounts`).
```bash
codex-account init
```

### 2. Add an Account
You can add accounts interactively or via flags.
```bash
# Interactive Wizard
codex-account add

# One-liner
codex-account add work-production --email dev@corp.com --api-key sk-prod-123
```

### 3. List Accounts
View all managed accounts. API keys are masked by default.
```bash
codex-account list

# Show full details (Use with caution!)
codex-account list --show-secrets

# JSON output for scripting
codex-account list --json
```

### 4. Switch Context
Activate an account. This updates `~/.codex/auth.json` so the Codex CLI uses these credentials.
```bash
codex-account switch work-production

# Verify status
codex-account status
```

### 5. Migration
Import accounts from the legacy backups folder.
```bash
codex-account migrate --from ../old-project
```

### 6. Interactive Mode (TUI)
Browse and select accounts using arrow keys.
```bash
codex-account tui
# or alias
codex-account interactive
```

### 7. Organization
Tag accounts and filter lists.
```bash
# Add with tags
codex-account add dev-account --tag work --tag v2

# Filter list
codex-account list --tag work
```

### 8. Shell Integration (Auto-Switch)
Detect `.codex-account` files in directories and auto-switch.
Add this to your `.zshrc` or `.bashrc`:
```bash
# Example ZSH hook
function chpwd() {
    if codex-account hook &> /dev/null; then
        target=$(codex-account hook)
        codex-account switch "$target"
    fi
}
```

## 🧪 Development

### Running Tests
```bash
poetry run pytest
```

### Project Structure
*   `src/codex_account_manager`: Source code.
*   `tests/`: Pytest suite (covers functionality, config security, migration).

## 🔒 Security Note
This tool manages sensitive API keys.
*   Storage is rooted at `~/.codex-accounts/`.
*   Files are readable **only by the user** (0600).
*   Avoid running as root.
