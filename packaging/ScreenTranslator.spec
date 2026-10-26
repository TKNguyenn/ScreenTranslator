# Build with: python -m PyInstaller --noconfirm packaging/ScreenTranslator.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
import sys
import comtypes.client

root = Path(SPECPATH).parent
uia = comtypes.client.GetModule("UIAutomationCore.dll")
datas = [(str(root / "app" / "assets"), "app/assets"),
         (str(root / "app" / "defaults"), "app/defaults")]
datas += collect_data_files("rapidocr_onnxruntime") + collect_data_files("uiautomation")
datas += collect_data_files("onnxruntime", includes=["LICENSE", "ThirdPartyNotices.txt"])
for package in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "numpy", "opencv-python",
                "onnxruntime", "rapidocr_onnxruntime", "Pillow", "shapely", "pyclipper", "PyYAML",
                "comtypes", "uiautomation", "pynput", "keyboard", "pyperclip", "python-dotenv",
                "httpx", "httpcore", "anyio", "certifi", "idna", "h11", "six", "tqdm"):
    datas += copy_metadata(package)
datas += [(str(Path(sys.base_prefix) / "LICENSE.txt"), "licenses/Python"),
          (str(root / "packaging" / "licenses"), "licenses")]
a = Analysis([str(root / "main.py")], pathex=[str(root)], datas=datas,
             hiddenimports=["pynput.mouse._win32", "pynput.keyboard._win32", "keyboard._winkeyboard",
                            "comtypes.gen.UIAutomationClient", "PySide6.QtSvg"],
             excludes=["tkinter", "matplotlib", "torch", "tensorflow", "pandas", "IPython", "pytest", "pygments"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ScreenTranslator",
          console=False, debug=False, strip=False, upx=False,
          icon=str(root / "app" / "assets" / "app_icon.ico"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ScreenTranslator")
