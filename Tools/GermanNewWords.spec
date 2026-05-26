# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\HOANG PHI LONG DANG\\repos\\German_NewWords\\Tools\\src\\\\gnw\\\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'numpy', 'pandas', 'scipy', 'matplotlib', 'sklearn', 'tensorflow', 'torch', 'transformers', 'IPython', 'jedi', 'parso'],
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
    name='GermanNewWords',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
