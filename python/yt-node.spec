# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for YT Booster Engine (yt-node).
Compiles the entire FastAPI application, background poller, and dependencies into a single binary.

Usage:
  macOS:   pyinstaller yt-node.spec
  Windows: pyinstaller yt-node.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Base directory is the directory of this spec file (python/)
base_dir = Path('.').resolve()

datas = []
for src_rel, dest_rel in [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
    ('app/extensions', 'app/extensions'),
    ('.env.example', '.'),
]:
    src_p = base_dir / src_rel
    if src_p.exists():
        datas.append((src_rel, dest_rel))

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'fastapi',
    'pydantic',
    'pydantic_settings',
    'pydantic_core',
    'httpx',
    'aiohttp',
    'websockets',
    'websockets.legacy',
    'websockets.legacy.server',
    'websockets.legacy.client',
    'pyngrok',
    'jinja2',
    'psutil',
    'selenium',
    'webdriver_manager',
    'dotenv',
    'email.mime.text',
    'email.mime.multipart',
]

a = Analysis(
    ['run.py'],
    pathex=[str(base_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='yt-node',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True so child process stdout/stderr can be piped to Tauri
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
