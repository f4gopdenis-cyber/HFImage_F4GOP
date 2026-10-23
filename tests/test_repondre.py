"""1.30 : « Répondre… » met toujours l'indicatif du correspondant en tête du message."""
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Repondre(unittest.TestCase):
    def setUp(self):
        try:
            import app
            import msgwin
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as e:
            self.skipTest(str(e))
        self.app_mod, self.msgwin = app, msgwin
        box = tk.Text(self.root)
        a = types.SimpleNamespace(txt_msg=box, win_txt=self.root, show_text=lambda: None, opnames={},
                                  online={}, heard={}, mycall=lambda: "F4GOP", myname=lambda: "Denis")
        for n in ("_station_call", "_full_call"):
            setattr(a, n, getattr(app.App, n).__get__(a))
        self.a, self.box = a, box

    def tearDown(self):
        self.root.destroy()
        # objets Tk libérés ici, dans le fil principal (sinon Tcl s'arrête net si le ramasse-miettes
        # passe plus tard dans le fil d'un autre essai)
        self.a = self.box = self.root = None
        import gc
        gc.collect()

    def reply(self, call, ask=True):
        w = types.SimpleNamespace(items=[{"call": call}], pos=0, app=self.a)
        asked = []
        with mock.patch.object(self.msgwin.messagebox, "askyesno", lambda *a, **k: asked.append(1) or ask):
            self.msgwin.MessageWindow.reply(w)
        return self.box.get("1.0", "end").strip(), asked

    def test_case_vide(self):
        txt, asked = self.reply("F4EEH")
        self.assertEqual((txt, asked), ("F4EEH de F4GOP :", []))

    def test_ancien_message_envoye_remplace(self):
        self.box.insert("1.0", "CQ de F4GOP, belle image !")
        self.a._last_sent_text = "CQ de F4GOP, belle image !"
        txt, asked = self.reply("M7WUV ANDY")                 # indicatif + prénom (ancienne version)
        self.assertEqual((txt, asked), ("M7WUV de F4GOP :", []))

    def test_brouillon_demande(self):
        self.box.insert("1.0", "texte pas encore envoyé")
        txt, asked = self.reply("F4EEH", ask=False)
        self.assertEqual((txt, asked), ("texte pas encore envoyé", [1]))
        txt, asked = self.reply("F4EEH", ask=True)
        self.assertEqual(txt, "F4EEH de F4GOP :")

    def test_inconnu(self):
        txt, _ = self.reply("?")
        self.assertEqual(txt, "de F4GOP :")


if __name__ == "__main__":
    unittest.main()
