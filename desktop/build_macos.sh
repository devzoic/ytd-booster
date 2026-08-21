#!/bin/bash
# ==============================================================================
# YT Booster - macOS 1-Click Desktop App Builder
# ==============================================================================
set -e

echo "🚀 Step 1: Compiling Python Engine into Standalone Binary..."
cd ../python
if [ -d "venv" ]; then
    source venv/bin/activate
fi
pip install pyinstaller -q
pyinstaller yt-node.spec --noconfirm

echo "📦 Step 2: Copying Engine Binary to Tauri Sidecars..."
mkdir -p ../desktop/src-tauri/binaries
TARGET_TRIPLE=$(rustc -Vv | grep host | cut -f2 -d' ')
cp dist/yt-node "../desktop/src-tauri/binaries/yt-node-$TARGET_TRIPLE"
cp dist/yt-node "../desktop/src-tauri/binaries/yt-node"

echo "🎨 Step 3: Building Tauri macOS Application (.dmg)..."
cd ../desktop
npx @tauri-apps/cli build

echo ""
echo "=============================================================================="
echo "  ✅ BUILD COMPLETE!"
echo "  🎁 Your macOS Installer (.dmg) is ready in:"
echo "     desktop/src-tauri/target/release/bundle/dmg/"
echo "=============================================================================="
