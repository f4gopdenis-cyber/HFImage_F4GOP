"""Version 0.91 : traduction des messages reçus dans la langue du programme."""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import translate  # noqa: E402

# réponse type de translate.googleapis.com (client=gtx)
GOOGLE = [[["Hello Denis, thanks for the nice picture. ", "Bonjour Denis, merci pour la belle image. ", None, None, 10],
           ["73", "73", None, None, 10]], None, "fr"]
MYMEMORY = {"responseData": {"translatedText": "Hello Denis", "match": 0.9},
            "matches": [{"source": "fr-FR", "target": "en-GB"}]}


class FakeResp:
    def __init__(self, obj):
        self.b = json.dumps(obj).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Traduction(unittest.TestCase):
    def test_google(self):
        with mock.patch.object(translate.urllib.request, "urlopen", lambda req, timeout, **k: FakeResp(GOOGLE)):
            out = translate.translate("Bonjour Denis, merci pour la belle image. 73", "en")
        self.assertEqual(out, ("Hello Denis, thanks for the nice picture. 73", "fr"))

    def test_deja_dans_la_bonne_langue(self):
        with mock.patch.object(translate.urllib.request, "urlopen", lambda req, timeout, **k: FakeResp(GOOGLE)):
            self.assertIsNone(translate.translate("Bonjour Denis, merci pour la belle image.", "fr"))

    def test_secours_mymemory(self):
        def urlopen(req, timeout, **k):
            if "googleapis" in req.full_url:
                raise OSError("bloqué")
            self.assertIn("langpair=Autodetect%7Cen", req.full_url)
            return FakeResp(MYMEMORY)
        with mock.patch.object(translate.urllib.request, "urlopen", urlopen):
            self.assertEqual(translate.translate("Bonjour Denis, merci", "en"), ("Hello Denis", "fr"))

    def test_sans_internet(self):
        def urlopen(req, timeout, **k):
            raise OSError("pas de réseau")
        with mock.patch.object(translate.urllib.request, "urlopen", urlopen):
            self.assertIsNone(translate.translate("Bonjour Denis, merci pour l'image", "en"))

    def test_rien_a_traduire(self):
        def urlopen(req, timeout, **k):
            raise AssertionError("pas d'appel réseau pour si peu")
        with mock.patch.object(translate.urllib.request, "urlopen", urlopen):
            for t in ("73", "F4GOP", "", "  ", "5/9 73"):
                self.assertIsNone(translate.translate(t, "en"), t)


class Fenetre(unittest.TestCase):
    def test_affichage(self):
        try:
            import tkinter as tk
            import msgwin
            root = tk.Tk()
        except Exception as e:
            self.skipTest(str(e))
        root.conf = {"msg_popup": False, "msg_translate": True}
        root._save_conf_file = lambda: None
        root._translate_ui = lambda w: None
        w = msgwin.MessageWindow(root)
        w.add({"id": 7, "call": "M0JGM", "text": "Hello Denis, nice picture", "utc": "15:40"}, popup=False)
        w.set_translation(7, "Hello Denis, nice picture", "Bonjour Denis, belle image", "EN → FR")
        shown = w.txt.get("1.0", "end")
        self.assertTrue(shown.startswith("Bonjour Denis, belle image"))
        self.assertIn("Original (EN → FR) :", shown)
        self.assertIn("Hello Denis, nice picture", shown)
        # 0.94 : le bouton « Répondre… » reste visible, même fenêtre réduite au minimum
        w.deiconify()
        w.geometry("460x280")
        for _ in range(5):
            w.update()
        shown_btns = [c.cget("text") for f in w.winfo_children() for c in f.winfo_children()
                      if c.winfo_class() == "TButton" and c.winfo_ismapped()]
        self.assertIn("Répondre…", shown_btns)
        self.assertIn("Fermer", shown_btns)
        root.conf["msg_translate"] = False
        w.show()
        self.assertEqual(w.txt.get("1.0", "end").strip(), "Hello Denis, nice picture")
        root.destroy()


if __name__ == "__main__":
    unittest.main()
