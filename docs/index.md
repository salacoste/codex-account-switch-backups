# Codex Account Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/salacoste/codex-account-switch-backups/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://github.com/salacoste/codex-account-switch-backups/blob/main/pyproject.toml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: AES-256](https://img.shields.io/badge/Security-AES--256-green)](https://github.com/salacoste/codex-account-switch-backups/blob/main/SECURITY.md)

> **The Professional's Choice for Secure Multi-Account Management.**  
> Stop juggling API keys in plaintext files. Switch identities instantly, securely, and confidently.

![Codex Account Manager Vault](assets/hero_vault.png)

---

## 🛑 The Problem

Modern development involves juggling dozens of API keys, tokens, and environments.
*   **Security Risks**: Leaving API keys in `.env` files or hardcoded in scripts leads to leaks.
*   **Context Errors**: Accidentally running a destructive command against `production` because you forgot to switch variables.
*   **Workflow Friction**: Manually copying and pasting tokens between terminals breaks flow.

![Chaos vs Order - The Problem vs The Solution](assets/chaos_vs_order.png)

## ✅ The Solution

**Codex Account Manager** is your secure, encrypted vault for professional identity management. It separates your credentials from your code, handles the complexity of secure storage, and injects authentication exactly where it's needed—on demand.

### Why Codex Account Manager?

🛡️ **Military-Grade Security**  
Your credentials are never stored in plaintext. We use **AES-256 encryption** with industry-standard key derivation. Files are strictly permission-locked (`chmod 600`), ensuring only *you* have access.

⚡ **Lightning-Fast Context Switching**  
Switching from "Personal Dev" to "Corporate Prod" takes one command. The CLI instantly updates your authentication context, so every subsequent tool uses the correct identity.

🧠 **Smart & Context Aware**  
Stop guessing "Am I in prod?". Link directories to specific accounts. When you `cd` into your work project, the manager automatically switches your identity for you.

🤝 **Built for Teams**  
Securely share credentials with your team without using insecure channels like Slack or Email. Synchronize encrypted vaults via private Git repositories.

📊 **Usage Tracking & Quotas**  
Stay on top of your consumption. The CLI tracks your API usage against 5h and Weekly limits, displaying progress bars so you never hit a rate limit unexpectedly.

![Codex Account Manager Terminal UI](assets/cli_tui.png)

---

## 🚀 Features

*   **Universal Proxy**: Inject credentials into any command (`codex-account run -- python script.py`) without polluting your global environment.
*   **Audit Logging**: Every access is logged locally. Know exactly when and which key was used.
*   **Legacy Migration**: Effortlessly import accounts from older project structures or backups.
*   **Terminal UI**: Forget the names? Browse your vault with a beautiful interactive TUI.
*   **Git Sync**: Keep your encrypted vault synchronized across all your devices using any private Git repo.

---

## 📖 Documentation

*   👉 **[Full User Guide](USER_GUIDE.md)**
*   👉 **[API Reference](api/api-contracts.md)**
*   👉 **[Development Guide](development/development-guide.md)**

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/salacoste/codex-account-switch-backups.git
cd codex-account-manager

# Install with Poetry
poetry install
poetry shell
```

## 🛠️ Quick Start

**1. Initialize your vault**
```bash
codex-account init
```

**2. Add your first account**
```bash
codex-account add work-prod --email me@corp.com --api-key sk-secure-123
```

**3. Switch Context**
```bash
codex-account switch work-prod
# You are now authenticated as 'work-prod'
```

**4. Check Status & Usage**
```bash
codex-account list
# Shows: Active | Name | Type | Usage (5h/W) | Tags
```

---

## 🧪 Development

### Running Tests
```bash
poetry run pytest
```

## 🤝 Community & Support

*   **Bug Reports**: [Open an Issue](https://github.com/salacoste/codex-account-switch-backups/issues/new?template=bug_report.yml)
*   **Feature Requests**: [Request a Feature](https://github.com/salacoste/codex-account-switch-backups/issues/new?template=feature_request.yml)
*   **Security**: See [Security Policy](https://github.com/salacoste/codex-account-switch-backups/blob/main/SECURITY.md).

## 🔒 Security Note

This tool manages sensitive API keys.
*   Storage is rooted at `~/.codex-accounts/`.
*   Files are readable **only by the user** (0600).
*   Avoid running as root.

## 📄 License

This project is licensed under the [MIT License](https://github.com/salacoste/codex-account-switch-backups/blob/main/LICENSE).
