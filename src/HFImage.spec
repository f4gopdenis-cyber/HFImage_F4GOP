# Spécification PyInstaller : exécutable Windows unique, sans console
a = Analysis(['app.py'], pathex=['.'],
             binaries=[('libcodec2.dll', '.')],
             datas=[('carte.bin', '.'), ('hfimage.ico', '.'), ('icon64.png', '.'), ('icon32.png', '.'), ('icon256.png', '.'), ('HFImage_mode_emploi.pdf', '.')],
             hiddenimports=["loopback", "msgwin", "clocktz", "trafic", "channel", "waterfall", "hybrid", "panel", "qsl", "i18n", "wavtext", "imgfmt", "stationmap", "presence", "theme", "updater", "tkinter.colorchooser", "paho.mqtt.client", "resvg_py", "tkinter.simpledialog",
                            "serial.tools.list_ports", "secrets", "hmac", "radio", "radiodlg", "gallery", "qrmfilter", "websync", "trafic", "wavanalyze", "anadlg", "riglist", "contextlib",
                            "xmlrpc.client", "comtypes", "comtypes.client", "comtypes.automation"],
             excludes=['scipy', 'skimage', 'matplotlib', 'pandas', 'IPython', 'pytest',
                       'PIL.ImageCms', 'numpy.f2py', 'numpy.testing', 'setuptools', 'pkg_resources', 'comtypes.test'])


def _keep(entry):
    name = entry[0].replace('\\', '/')
    if 'portaudio-binaries' in name and not name.endswith('libportaudio64bit.dll'):
        return False                      # ARM, 32 bits et ASIO inutiles ici
    if name.startswith(('_tcl_data/tzdata', '_tcl_data/msgs', '_tk_data/msgs', '_tk_data/images')):
        return False                      # fuseaux horaires, traductions et démos Tcl/Tk
    if name.endswith('_imagingcms.cp312-win_amd64.pyd'):
        return False
    return True


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='HFImage_F4GOP', console=False, upx=False, icon='hfimage.ico')
