# PyInstaller: jedan izvršni fajl sa svim (Python, aiohttp, mpy-cross, interfejs, ESP kod, primeri taktika).
#   pip install pyinstaller -r simulator/requirements.txt
#   pyinstaller simulator/eurosim.spec        ->  dist/eurosim  (Windows: dist/eurosim.exe)
# Pokreće se iz korena repoa (putanje ispod su relativne na koren).
import glob
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))


def files(pattern, dest):
    return [(f, dest) for f in glob.glob(os.path.join(ROOT, pattern)) if os.path.isfile(f)]


datas = []
for sub in ("", "vendor", "vendor/loaders", "vendor/utils", "models"):
    datas += files("simulator/web/%s/*.*" % sub if sub else "simulator/web/*.*", "simulator/web/" + sub)
datas += files("simulator/profiles/*.toml", "simulator/profiles")
datas += files("ESP32/lib/*.py", "ESP32/lib")
datas += files("ESP32/sim/*.py", "ESP32/sim")
datas += files("ESP32/tactics/*.py", "ESP32/tactics")
datas += files("ESP32/config.py", "ESP32")
datas += files("tools/espnet.py", "tools")

mc_datas, mc_bins, mc_hidden = collect_all("mpy_cross")
datas += mc_datas

# ESP kod se uvozi kao obični .py fajlovi u toku rada, pa PyInstaller ne vidi šta on uvozi iz standardne biblioteke
hidden = collect_submodules("eurosim") + collect_submodules("aiohttp") + mc_hidden + [
    "binascii", "gc", "hashlib", "json", "math", "os", "pathlib", "re", "socket", "struct", "tempfile",
    "time", "types", "shutil", "tomllib", "webbrowser", "random", "collections", "base64",
]

a = Analysis([os.path.join(SPECPATH, "eurosim_main.py")], pathex=[SPECPATH], binaries=mc_bins, datas=datas,
             hiddenimports=hidden, excludes=["tkinter", "PIL", "numpy", "pytest"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="eurosim", console=True, upx=False,
          runtime_tmpdir=None)
