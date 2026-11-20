from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_dynamic_libs

root = Path(SPECPATH).resolve()
site = Path(sys.prefix) / "Lib" / "site-packages"
datas = []
binaries = []
hidden = []

def additems(target, items):
    for item in items:
        if item not in target:
            target.append(item)

def addpkg(name):
    try:
        pkgdata, pkgbin, pkghidden = collect_all(name)
        additems(datas, pkgdata)
        additems(binaries, pkgbin)
        additems(hidden, pkghidden)
    except Exception:
        pass

for name in (
    "autoit",
    "cv2",
    "discord",
    "keyboard",
    "mouse",
    "mss",
    "numpy",
    "PIL",
    "pyautogui",
    "rapidocr_onnxruntime",
    "pygetwindow",
    "pynput",
    "pythonnet",
    "clr_loader",
    "requests",
    "ttkbootstrap",
    "webview",
    "win32",
    "win32com",
    "win32comext",
    "win32ctypes",
):
    addpkg(name)

try:
    additems(hidden, collect_submodules("biome_tracker"))
except Exception:
    pass
try:
    additems(hidden, collect_submodules("webview"))
except Exception:
    pass
try:
    additems(hidden, collect_submodules("onnxruntime.capi"))
    additems(binaries, collect_dynamic_libs("onnxruntime"))
except Exception:
    pass

additems(hidden, [
    "win32api",
    "win32clipboard",
    "win32con",
    "win32gui",
    "win32process",
    "win32com.client",
    "pythoncom",
    "pywintypes",
    "clr",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
])

def addfile(path, dest, target):
    if path.is_file():
        item = (str(path), dest)
        if item not in target:
            target.append(item)

if root.joinpath("lib").is_dir():
    datas.append((str(root / "lib"), "lib"))
addfile(root / "biome_tracker" / "NoteabBiomeTracker.ico", "biome_tracker", datas)
if root.joinpath("crafting_files_do_not_open").is_dir():
    datas.append((str(root / "crafting_files_do_not_open"), "crafting_files_do_not_open"))
if root.joinpath("config.json").is_file():
    datas.append((str(root / "config.json"), "."))

for name in ("AutoItX3.dll", "AutoItX3_x64.dll"):
    addfile(site / "autoit" / "lib" / name, "autoit/lib", binaries)

analysis = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="CoteabMacro",
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
    icon=str(root / "lib" / "official_release.ico"),
)