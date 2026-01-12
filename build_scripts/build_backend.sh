#!/bin/bash
set -e

# Ensure we are in the project root
cd "$(dirname "$0")/.."

echo "🏗️  Building codex-backend binary..."

# Clean previous builds
rm -rf build dist

# Run PyInstaller
# --onefile: Create a single executable
# --name: Name of the binary
# --paths: Add src to path
poetry run pyinstaller src/codex_account_manager/main.py \
    --name codex-backend \
    --onefile \
    --clean \
    --paths src \
    --hidden-import="codex_account_manager.commands.account" \
    --hidden-import="codex_account_manager.commands.auth" \
    --hidden-import="codex_account_manager.commands.limits"

echo "✅ Build complete! Binary located at:"
ls -lh dist/codex-backend

echo "📦 Installing binary to frontend..."
mkdir -p apps/web/src-tauri/binaries
cp dist/codex-backend apps/web/src-tauri/binaries/codex-backend-aarch64-apple-darwin
echo "Done."
