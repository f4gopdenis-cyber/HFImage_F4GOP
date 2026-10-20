"""Version 1.08 (demandes de RK1AT) : fichiers hybrides sans limite de taille ni de type,
image glissée / clic dans la fenêtre TX."""
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import hybrid  # noqa: E402


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


class Limite(unittest.TestCase):
    def tearDown(self):
        hybrid.set_max_download(200)

    def test_reglage(self):
        hybrid.set_max_download(8)
        self.assertEqual(hybrid.MAX_DOWNLOAD, 8 * 1024 * 1024)
        with self.assertRaises(hybrid.Refused):
            hybrid.download("https://example.org/x.zip", 9 * 1024 * 1024, 0)
        hybrid.set_max_download(0)                             # sans limite
        self.assertGreater(hybrid.MAX_DOWNLOAD, 100 * 1024 ** 3)

    def test_libelles(self):
        app = _app()
        self.assertEqual([app.App._rxmax_label(x) for x in (8, 200, 1024, 0)],
                         ["8 Mo", "200 Mo", "1 Go", "Sans limite"])


class Envoi(unittest.TestCase):
    def test_gros_fichier_en_hybride(self):
        app = _app()
        p = os.path.join(tempfile.mkdtemp(), "archive.xyz")
        with open(p, "wb") as f:
            f.write(os.urandom(17_000_000))                    # > 16 Mo, type quelconque
        sent = []
        s = types.SimpleNamespace(tx_busy=False, v_call=types.SimpleNamespace(get=lambda: "RK1AT"),
                                  v_hyb=types.SimpleNamespace(get=lambda: True), log=lambda m: None,
                                  _hyb_cfg=lambda: {"host": "ftp.x", "url": "https://x/"},
                                  transmit=lambda tx=None: sent.append(tx))
        with mock.patch.object(app.messagebox, "askyesno", lambda *a, **k: True), \
                mock.patch.object(app.messagebox, "showerror", lambda *a, **k: sent.append("refusé")):
            app.App.send_file(s, p)
        self.assertEqual(len(sent), 1)
        self.assertNotEqual(sent[0], "refusé")
        self.assertEqual(sent[0].fmt, "file")


class Glisser(unittest.TestCase):
    def test_image_ou_fichier(self):
        app = _app()
        d = tempfile.mkdtemp()
        img, doc = os.path.join(d, "photo.JPG"), os.path.join(d, "log.adi")
        for q in (img, doc):
            open(q, "wb").close()
        got = []
        s = types.SimpleNamespace(IMAGE_EXTS=app.App.IMAGE_EXTS, show_tab=lambda t: got.append(t),
                                  load_image=lambda p: got.append(("image", p)),
                                  send_file=lambda p: got.append(("fichier", p)))
        app.App._dropped(s, [img])
        with mock.patch.object(app.messagebox, "askyesno", lambda *a, **k: True):
            app.App._dropped(s, [doc])
        self.assertEqual(got, ["tx", ("image", img), ("fichier", doc)])

    def test_clic_ouvre_le_choix(self):
        app = _app()
        opened = []
        s = types.SimpleNamespace(_cmp_press=(10, 10), tx_busy=False, lb_cmp=types.SimpleNamespace(zoom=1.0),
                                  open_image=lambda: opened.append(1))
        app.App._cmp_click(s, types.SimpleNamespace(x=11, y=12))
        s._cmp_press = (10, 10)
        app.App._cmp_click(s, types.SimpleNamespace(x=80, y=12))       # glisser : non
        self.assertEqual(opened, [1])

    def test_depot_tkdnd(self):
        """1.09 : dépôt reçu par tkdnd (chemins avec espaces), sans fermer le programme."""
        import tkinter as tk
        import dropfiles
        try:
            root = tk.Tk()
        except tk.TclError as e:
            self.skipTest(str(e))
        got = []
        try:
            lab = tk.Label(root, text="x")
            lab.pack()
            try:
                ok = dropfiles.hook(root, dropfiles.all_widgets(root), got.append)
            except RuntimeError as e:
                self.skipTest(str(e))                           # tkdnd absent pour cette plate-forme
            if not ok:
                self.skipTest("tkinterdnd2 absent")
            script = lab.bind("<<Drop>>")
            name = [w for w in script.replace('"', " ").replace("[", " ").split() if w.endswith("on_drop")][0]
            args = ["copy", "copy", "1", "CF_HDROP", "x", "", "", "{C:/Mes images/photo 1.jpg} C:/b.png",
                    "<<Drop>>", "", "", "", "DND_Files", "", "", str(lab), "10", "10"]
            root.tk.call(name, *args)
            root.update()
            self.assertEqual(got, [["C:/Mes images/photo 1.jpg", "C:/b.png"]])
        finally:
            root.destroy()

if __name__ == "__main__":
    unittest.main()
