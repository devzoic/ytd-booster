@echo off
REM ==============================================================================
REM YT Booster - Windows 1-Click Desktop App Builder (.msi / .exe)
REM ==============================================================================
echo 🚀 Step 1: Compiling Python Engine into Standalone Windows Binary...
cd ..\python
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
pip install pyinstaller -q
pyinstaller yt-node.spec --noconfirm

echo 📦 Step 2: Copying Binary to Tauri Sidecars...
if not exist ..\desktop\src-tauri\binaries mkdir ..\desktop\src-tauri\binaries
copy /Y dist\yt-node.exe ..\desktop\src-tauri\binaries\yt-node-x86_64-pc-windows-msvc.exe
copy /Y dist\yt-node.exe ..\desktop\src-tauri\binaries\yt-node.exe

echo 🎨 Step 3: Building Tauri Windows Installer (.msi / .exe)...
cd ..\desktop
npx @tauri-apps/cli build

echo.
echo ==============================================================================
echo   ✅ BUILD COMPLETE!
echo   🎁 Your Windows Installer (.msi / .exe) is ready in:
echo      desktop\src-tauri\target\release\bundle\msi\
echo ==============================================================================
pause
