# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('config.py', '.'), ('app_icon.ico', '.'), ('MANUAL_DE_USUARIO.txt', '.')]
binaries = []
hiddenimports = []

# Incluir DLLs nativas C-Runtime para evitar error Failed to load Python DLL
import os, sys
sys_dir = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
for dll in ["vcruntime140.dll", "msvcp140.dll", "vcruntime140_1.dll", "vcomp140.dll"]:
    dll_path = os.path.join(sys_dir, dll)
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))

tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['bot.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Automatizador INVIMA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
