# Spécification PyInstaller : exécutable unique, sans console
# - Windows (HFImage_F4GOP.exe) ; sert aussi à la version Windows 7, compilée avec Python 3.8
# - Linux (HFImage_F4GOP_Linux) : libcodec2.so et libhamdrm.so compilées par release.yml
import sys
WIN = sys.platform.startswith("win")
LEGACY = sys.version_info < (3, 9)
_legacy = ["pillow_avif", "numpy.core._multiarray_tests"] if LEGACY else []   # Pillow 10 + numpy 1.24
# Windows 7 : resvg_py (Rust récent) appelle des fonctions de Windows 8 -> retiré ;
# la CRT universelle (dossier ucrt/, copié depuis le SDK Windows par release.yml) est embarquée
# pour les Windows 7 sans la mise à jour KB2999226.
import glob as _glob
import os as _os
# glisser-déposer : extension tkdnd de tkinterdnd2 (Windows 64 bits seulement)
try:
    import tkinterdnd2 as _dnd
    _dsub = 'win-x64' if WIN else 'linux-x64'
    _dnd_data = [(_os.path.join(_os.path.dirname(_dnd.__file__), 'tkdnd', _dsub), 'tkinterdnd2/tkdnd/' + _dsub)]
except ImportError:
    _dnd_data = []
_ucrt = [(f, '.') for f in _glob.glob('ucrt/*.dll')] if LEGACY else []
if WIN:
    _native = [('libcodec2.dll', '.'), ('hamdrm.dll', '.')]
else:
    # PortAudio du système (paquet libportaudio2), embarqué pour que le programme marche seul
    _pa = [p for p in ('/usr/lib/x86_64-linux-gnu/libportaudio.so.2', '/usr/lib/libportaudio.so.2')
           if _os.path.exists(p)]
    _native = [('libcodec2.so', '.'), ('libhamdrm.so', '.')] + [(p, '.') for p in _pa[:1]]
a = Analysis(['app.py'], pathex=['.'],
             binaries=_native + _ucrt,
             datas=[('carte.bin', '.'), ('hfimage.ico', '.'), ('icon64.png', '.'), ('icon32.png', '.'), ('icon256.png', '.'), ('hommage_vk4aes.jpg', '.'), ('HFImage_mode_emploi.pdf', '.'), ('HFImage_user_manual_EN.pdf', '.'), ('LICENSE.txt', '.'), ('LICENCE.txt', '.'), ('emoji/*.png', 'emoji')] + _dnd_data,
             hiddenimports=["loopback", "netssl", "certifi", "clip", "txedit", "icons", "docking", "rxclean", "translate", "setupwiz", "bubbles", "dropfiles", "tkinterdnd2", "tkinterdnd2.TkinterDnD", "msgwin", "clocktz", "trafic", "channel", "waterfall", "hybrid", "panel", "qsl", "i18n", "wavtext", "imgfmt", "stationmap", "presence", "theme", "updater", "tkinter.colorchooser", "paho.mqtt.client", "tkinter.simpledialog",
                            "serial.tools.list_ports", "secrets", "hmac", "radio", "radiodlg", "gallery", "qrmfilter", "websync", "sites", "tci", "flag", "email.utils", "trafic", "wavanalyze", "anadlg", "riglist", "contextlib",
                            "xmlrpc.client", "buildinfo", "hamdrm", "easypal_hybrid", "PIL._tkinter_finder", "PIL.ImageTk"] + (["comtypes", "comtypes.client", "comtypes.automation"] if WIN else [])
                           + _legacy + ([] if LEGACY else ["resvg_py"]),
             excludes=['scipy', 'skimage', 'matplotlib', 'pandas', 'IPython', 'pytest',
                       'PIL.ImageCms', 'numpy.f2py', 'numpy.testing', 'setuptools', 'pkg_resources', 'comtypes.test'] + (['resvg_py'] if LEGACY else []))


def _keep(entry):
    name = entry[0].replace('\\', '/')
    if 'portaudio-binaries' in name and not name.endswith('libportaudio64bit.dll'):
        return False                      # ARM, 32 bits et ASIO inutiles ici
    if name.startswith(('_tcl_data/tzdata', '_tcl_data/msgs', '_tk_data/msgs', '_tk_data/images')):
        return False                      # fuseaux horaires, traductions et démos Tcl/Tk
    if name.split('/')[-1].startswith('_imagingcms.'):
        return False
    return True


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='HFImage_F4GOP' if WIN else 'HFImage_F4GOP_Linux', console=False, upx=False,
          icon='hfimage.ico' if WIN else None, strip=False)   # strip abîme la bibliothèque de numpy (openblas)
