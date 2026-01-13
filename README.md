# Codex Account Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: AES-256](https://img.shields.io/badge/Security-AES--256-green)](SECURITY.md)

> **The Professional's Choice for Secure Multi-Account Management.**  
> Stop juggling API keys in plaintext files. Switch identities instantly, securely, and confidently.

![Codex Account Manager Vault](docs/assets/hero_vault.png)

---

## 🛑 The Problem: Quota Chaos & Key Fatigue

Modern AI Development creates a new set of challenges:
*   **Quota Limits**: You have 3 different OpenAI/Codex accounts to manage 5h and Weekly limits. Hitting a limit mid-stream breaks your flow.
*   **Context Risks**: Accidentally running a heavy "Thinking Model" task on your personal limited account instead of the corporate unlimited plan.
*   **Security Nightmares**: Storing sensitive `sk-` keys in `.env` files scattered across projects is a leak waiting to happen.

![Chaos vs Order - The Problem vs The Solution](docs/assets/chaos_vs_order.png)

## ✅ The Solution

**Codex Account Manager** is your unified command center for AI credentials. It treats your identities as **Profiles**, not just text strings.

### Why Codex Account Manager?

🧠 **Intelligent Quota Management**  
Never hit a rate limit blindly again. The system tracks your **5-Hour** and **Weekly** usage for every account in real-time. Know exactly which account has capacity *before* you switch.

⚡ **Instant Context Switching**  
Switch from "Personal (Limited)" to "Work (Pro)" in one keystroke. The CLI instantly injects the correct credentials into your environment, ensuring zero downtime when one account hits its cap.

🖥️ **Native macOS Experience**  
**Always there, never in the way.** Our native System Tray application sits quietly in your menu bar. 
*   **Glanceable Status**: See your active account and usage usage bars directly in the menu.
*   **One-Click Switch**: Change identities without touching the terminal.
*   **Global Hotkey**: Bring up the dashboard instantly.

🛡️ **Military-Grade Security**  
Your credentials are never stored in plaintext. We use **AES-256 encryption** strictly permission-locked (`chmod 600`), ensuring only *you* have access.

---

## 🚀 Features

*   **Universal Proxy**: Inject credentials into any command (`codex-account run -- python script.py`) without polluting your global environment.
*   **Audit Logging**: Every access is logged locally. Know exactly when and which key was used.
*   **Legacy Migration**: Effortlessly import accounts from older project structures.
*   **Terminal UI**: Forget the names? Browse your vault with a beautiful interactive TUI.
*   **Git Sync**: Keep your encrypted vault synchronized across all your devices using any private Git repo.

![Codex Account Manager Terminal UI](docs/assets/cli_tui.png)

---

## 📖 Documentation

Visit our full documentation site for detailed guides:
👉 **[User Guide & Documentation](https://salacoste.github.io/codex-account-switch-backups/)**

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

*   **Bug Reports**: [Open an Issue](.github/ISSUE_TEMPLATE/bug_report.yml)
*   **Feature Requests**: [Request a Feature](.github/ISSUE_TEMPLATE/feature_request.yml)
*   **Security**: See [Security Policy](SECURITY.md).

## 🔒 Security Note

This tool manages sensitive API keys.
*   Storage is rooted at `~/.codex-accounts/`.
*   Files are readable **only by the user** (0600).
*   Avoid running as root.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
