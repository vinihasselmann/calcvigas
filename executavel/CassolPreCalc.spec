# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = os.path.abspath(os.path.join(SPECPATH, ".."))
streamlit_datas, streamlit_binaries, streamlit_hidden = collect_all("streamlit")

datas = streamlit_datas + [
    (os.path.join(project_root, "app.py"), "."),
    (os.path.join(project_root, "pages"), "pages"),
    (os.path.join(project_root, "assets"), "assets"),
    (os.path.join(project_root, ".streamlit"), ".streamlit"),
    (os.path.join(project_root, "data", "laje_alv_base.xlsx"), "data"),
]

hiddenimports = streamlit_hidden
hiddenimports += collect_submodules("engine")
hiddenimports += collect_submodules("ui")
hiddenimports += [
    "data.lp_table",
    "numpy",
    "openpyxl",
    "pandas",
    "tqdm",
    "xlsxwriter",
]

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[project_root],
    binaries=streamlit_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CassolPreCalc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CassolPreCalc",
)
