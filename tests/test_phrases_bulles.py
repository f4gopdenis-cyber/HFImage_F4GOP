"""1.45 (demande de M7WUV) : phrases toutes prêtes pour les bulles, et dernier style de bulle retenu."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import i18n  # noqa: E402


def _app():
    try:
        import app
        return app
    except (ImportError, OSError) as e:
        raise unittest.SkipTest(str(e))


def fake(conf=None, call="F4GOP", name="Denis", loc="IN98QR"):
    app = _app()
    s = types.SimpleNamespace(conf=dict(conf or {}), DEFAULT_PHRASES=app.App.DEFAULT_PHRASES)
    s.mycall = lambda: call
    s.myname = lambda: name
    s.v_loc = types.SimpleNamespace(get=lambda: loc)
    s._bubble_phrases = lambda: app.App._bubble_phrases(s)
    s._phrase_fill = lambda p: app.App._phrase_fill(s, p)
    return app, s


class Phrases(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("fr")

    def test_liste_de_depart_traduite(self):
        app, s = fake()
        i18n.set_lang("fr")
        self.assertIn("Bonjour de {MOI}", s._bubble_phrases())
        i18n.set_lang("en")
        self.assertIn("Good morning de {CALL}", s._bubble_phrases())
        self.assertEqual(len(s._bubble_phrases()), len(app.App.DEFAULT_PHRASES))

    def test_remplacements(self):
        app, s = fake()
        self.assertEqual(s._phrase_fill("Bonjour de {MOI}"), "Bonjour de F4GOP")
        self.assertEqual(s._phrase_fill("Good afternoon de {CALL}"), "Good afternoon de F4GOP")
        self.assertEqual(s._phrase_fill("{MOI} — {PRENOM} — {LOC}"), "F4GOP — Denis — IN98QR")
        self.assertEqual(s._phrase_fill("{call} {name}"), "F4GOP Denis")
        app, s = fake(name="")
        self.assertEqual(s._phrase_fill("{MOI} — {PRENOM} — {LOC}"), "F4GOP — IN98QR")

    def test_liste_personnelle(self):
        app, s = fake({"bub_phrases": ["Good Afternoon de M7WUV", "", "73 {CALL}"]})
        self.assertEqual(s._bubble_phrases(), ["Good Afternoon de M7WUV", "73 {CALL}"])
        app, s = fake({"bub_phrases": []})                    # liste vidée volontairement
        self.assertEqual(s._bubble_phrases(), [])


class FenetreBulles(unittest.TestCase):
    def test_menu_et_style_retenu(self):
        import gc
        import json
        import tempfile
        from unittest import mock
        from PIL import Image
        app = _app()
        d = tempfile.mkdtemp()
        conf = os.path.join(d, "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "M7WUV", "licence_ok": "1.0", "lang": "en",
                       "bub_last": {"style": "texte", "size": "grande", "bg": "#000000", "fg": "#0000ff"}}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                a.withdraw()
                a.src_img = Image.new("RGB", (320, 240), (40, 90, 140))
                a.bubble_dialog()
                a.update()
                b = a.bubbles[-1]
                # nouvelle bulle : style retenu (texte seul, grand, bleu sur noir)
                self.assertEqual((b["style"], b["size"], b["fg"]), ("texte", "grande", "#0000ff"))
                w = a._bub_win
                mbs = [x for x in _walk(w) if x.winfo_class() == "TMenubutton"]
                self.assertEqual(len(mbs), 1)
                menu = a.nametowidget(mbs[0].cget("menu"))
                menu.tk.call(menu, "post", 0, 0)              # postcommand : remplit le menu
                menu.unpost()
                labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                          if menu.type(i) == "command"]
                self.assertIn("Good morning de M7WUV", labels)
                menu.invoke(labels.index("Good evening de M7WUV"))
                a.update()
                self.assertEqual(a.bubbles[-1]["text"], "Good evening de M7WUV")
                a.bubbles[-1]["fg"] = "#ff0000"
                a.tk.eval(w.protocol("WM_DELETE_WINDOW"))         # fermeture (OK)
                a.update()
                self.assertEqual(a.conf["bub_last"]["fg"], "#ff0000")
            finally:
                a.destroy()
                gc.collect()


def _walk(w):
    for c in w.winfo_children():
        yield c
        yield from _walk(c)


if __name__ == "__main__":
    unittest.main()
