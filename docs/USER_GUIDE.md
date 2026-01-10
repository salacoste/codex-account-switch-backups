# Codex Account Manager: User Guide

Welcome to the **Codex Account Manager**! This guide covers everything you need to know to install, configure, and use the tool effectively.

## 📚 Table of Contents
1.  [Installation](#installation)
2.  [Getting Started](#getting-started)
3.  [Daily Workflow](#daily-workflow)
4.  [Organization (Tags & Lists)](#organization)
5.  [Universal Proxy (Run)](#universal-proxy-run-command)
6.  [Context Awareness](#context-awareness)
7.  [Data Portability & Sync](#data-portability--sync)
8.  [Security & Auditing](#security--auditing)
9.  [Troubleshooting](#troubleshooting)

---

## 1. Installation

### Prerequisites
*   Python 3.9 or higher
*   Pip (Python Package Installer)

### Install via Pip
If you have the `.whl` file (from the build):
```bash
pip install codex_account_manager-1.0.0-py3-none-any.whl
```

### Install from Source
```bash
git clone https://github.com/your-org/codex-account-backups.git
cd codex-account-manager
poetry install
poetry shell
```

---

## 2. Getting Started

### Initialize Storage
Before using the tool, you must initialize the secure storage vault. This creates the `~/.codex-accounts` directory with secure permissions (`0600`).

```bash
codex-account init
```

### Add Your First Account
You can add an account using the interactive wizard:
```bash
codex-account add
```
Follow the prompts to enter:
*   **Name**: A unique nickname (e.g., `work`, `personal`).
*   **Email**: Your registered email (e.g., `alice@example.com`).
*   **API Key**: Your Codex API Key (`sk-...`).

---

## 3. Daily Workflow

### Switching Accounts
The core feature of this tool is **Context Switching**. When you switch accounts, the tool updates the central `~/.codex/auth.json` file used by the Codex CLI.

**Command:**
```bash
codex-account switch <name>
```

**Example:**
```bash
codex-account switch work
# You are now authenticated as "work"
```

### Checking Status
Unsure which account is active?
```bash
codex-account status
```
Output:
```text
✅ Active Identity: work (alice@work.com)
```

### Interactive Selection (TUI)
If you forget your account names, use the interactive browser:
```bash
codex-account tui
```
Use **Arrow Keys** to highlight an account and **Enter** to switch.

---

## 4. Organization

### Tagging Accounts
Group your accounts logically using tags (e.g., `v1`, `v2`, `prod`, `dev`).

**Add with Tags:**
```bash
codex-account add project-x --tag dev --tag cloud-v2
```

### Filtering Lists
View only relevant accounts:
```bash
codex-account list --tag dev
```

---

---

## 5. Universal Proxy (Run Command)
The superpower of Codex Account Manager is the ability to inject credentials into *any* other CLI tool without manual exports.

### Basic Usage
Use `codex-account run` to wrap your target command.

```bash
# Injects CODEX_API_KEY and CODEX_ACCESS_TOKEN
codex-account run -- python deploy.py
```

### Environment Variables
You can attach arbitrary environment variables (like AWS keys, Database URLs) to an account.

**Add Variable:**
```bash
codex-account env add AWS_ACCESS_KEY_ID AKIA...
codex-account env add AWS_SECRET_ACCESS_KEY wJal...
```

**Run with Vars:**
```bash
codex-account run -- aws s3 ls
```

---

## 6. Context Awareness
Stop switching accounts manually. Link directories to specific identities.

### Link Directory
```bash
cd ~/projects/client-alpha
codex-account context set client-alpha
```
Now, this directory is permanently linked to `client-alpha`.

### Session Override
You can also override the account for a specific terminal session (useful for temporary work):

```bash
export CODEX_ACTIVE_ACCOUNT=personal
codex-account run -- ./script.sh  # Uses 'personal' regardless of global settings
```

---

## 7. Data Portability & Sync
Keep your accounts backed up and synchronized across devices.

### Manual Backup (Zip)
```bash
# Access denied? Encryption protects your data.
codex-account export --output ./backup.zip
# Restore
codex-account import ./backup.zip
```

### Git Sync (Recommended)
Sync your encrypted vault to a private Git repository.

**Setup:**
1. Create a private repo (e.g., on GitHub/GitLab).
2. Initialize sync:
   ```bash
   codex-account sync init git@github.com:me/my-vault.git
   ```

**Workflow:**
```bash
codex-account sync push  # Upload changes
codex-account sync pull  # Download changes
```

---

## 8. Security & Auditing
Track who accessed your keys and when.

### View Audit Log
```bash
codex-account audit
```

### Filter Logs
```bash
codex-account audit --limit 10 --account work
```

---

## 9. Troubleshooting

### "Permission Denied" Errors
Ensure your `~/.codex-accounts` directory has correct permissions.
Fix it manually:
```bash
chmod 700 ~/.codex-accounts
chmod 600 ~/.codex-accounts/*/auth.json
```

### "Account Not Found"
Run `codex-account list` to see available names. Names are "slugified" (e.g., "My Account" becomes "my-account").

### Manual Recovery
If the tool breaks, your data is stored in standard JSON files at `~/.codex-accounts/`. You can back up or inspect this directory manually (requires root or user permissions).

---

## 10. Agile Teams (Team Vaults)

Collaborate securely with shared team vaults.

### Join a Team
You need the **Team Name**, **Git URL**, and the **Team Master Key** (from your admin).

```bash
codex-account team join ops git@github.com:my-org/ops-vault.git
```
Enter the Team Master Key when prompted.

### Access Team Accounts
Team accounts are namespaced: `team-name/account-name`.

```bash
# List all accounts (Personal + Teams)
codex-account list

# Switch to a team account
codex-account switch ops/aws-prod
```
The tool handles fetching the correct encryption key automatically.
