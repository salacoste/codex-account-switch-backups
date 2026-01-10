# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-01-10

### Added
- **Team Vaults**: Mount multiple shared repositories via `codex-account team join`.
- **Namespaced Access**: Access accounts via `team/account`.
- **CI/CD**: Added GitHub Actions workflows for testing and release.
- **Security Policy**: Added `SECURITY.md`.

### Changed
- **Architecture**: Refactored `ConfigManager` to support multi-vault architecture.
- **Dependencies**: Updated `pyproject.toml` to stricter versions.

## [2.3.0] - 2026-01-09
### Added
- **Audit Logging**: Secure centralized logging of all credential access.

## [2.2.0] - 2026-01-09
### Added
- **Context Awareness**: `local_context` command for directory linking.
- **Session Support**: `CODEX_ACTIVE_ACCOUNT` env var override.

## [2.0.0] - 2026-01-09
### Added
- **Universal Proxy**: `codex-account run` (The "Inject" command).
- **Environment Management**: `codex-account env add`.

## [1.5.0] - 2026-01-09
### Added
- **Portability**: `export` and `import` commands (Zip formatted).
- **Git Sync**: `sync push` and `pull` for personal vaults.

## [1.0.0] - 2026-01-09
### Added
- Initial Release.
- Secure Storage (AES-256).
- CRUD Commands (`add`, `list`, `remove`, `switch`).
- Legacy Migration (`migrate`).
