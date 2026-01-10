# Contributing to Codex Account Manager

First off, thanks for taking the time to contribute! ❤️

All types of contributions are encouraged and valued. See the [Table of Contents](#table-of-contents) for different ways to help and details about how this project handles them. Please make sure to read the relevant section before making your contribution. It will make it a lot easier for us maintainers and smooth out the experience for all involved. The community looks forward to your contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [I Have a Question](#i-have-a-question)
- [I Want To Contribute](#i-want-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project and everyone participating in it is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code.

## I Have a Question

Usage questions can be asked in GitHub Discussions.
Before you ask a question, it is best to search for existing Issues that might help you.

## I Want To Contribute

### Reporting Bugs

- **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/salacoste/codex-account-switch-backups/issues).
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/salacoste/codex-account-switch-backups/issues/new).
- Include a *title and clear description*, as much relevant information as possible, and a *code sample* or an *executable test case* demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements

- Open a new issue with the label `enhancement`.
- Clearly describe the behavior you would like to see.
- Explain why this enhancement would be useful to most users.

### Pull Requests

1.  Fork the repo and create your branch from `main`.
2.  If you've added code that should be tested, add tests.
3.  If you've changed APIs, update the documentation.
4.  Ensure the test suite passes (`poetry run pytest`).
5.  Make sure your code lints (`poetry run ruff check .`).
6.  Issue that pull request!

## Development Setup

```bash
git clone https://github.com/salacoste/codex-account-switch-backups.git
cd codex-account-manager
poetry install
poetry shell
```
