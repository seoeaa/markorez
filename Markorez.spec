# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

datas = []
binaries = []
hiddenimports = []

# customtkinter
tmp = collect_all('customtkinter')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

# PIL / Pillow
tmp = collect_all('PIL')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

# OpenCV
tmp = collect_all('cv2')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

# numpy
tmp = collect_all('numpy')
datas += tmp[0]; binaries += tmp[1]; hiddenimports += tmp[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['cv2', 'numpy', 'PIL', 'customtkinter', 'image_utils', 'canvas_widget', 'editor_window', 'constants'],
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
    name='Markorez',
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
)
