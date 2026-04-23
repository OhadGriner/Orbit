#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing PyInstaller..."
uv add --dev pyinstaller

echo "Building EyeTrackingGame.app..."
uv run pyinstaller main.spec --clean --noconfirm

echo ""
echo "Done! App is at: dist/EyeTrackingGame.app"
echo "To run it:  open dist/EyeTrackingGame.app"
