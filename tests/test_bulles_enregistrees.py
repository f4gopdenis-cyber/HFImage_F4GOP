"""2.40 (demande de VK6NJP) : bulles enregistrées avec leur style (texte, style, couleurs, taille,
émoticônes animées, vitesse du bandeau, place), remises d'un clic sur l'image TX."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_edition_directe as ted  # noqa: E402

E = ted.E


class BullesEnregistrees(ted.EditionDirecte):
    test_ajouter_deplacer_agrandir_texte = None
    test_logo_png_et_menu = None

    def test_enregistrer_et_remettre(self):
        a, ed = self.a, self.ed
        a.conf["bub_saved"] = []
        ed.add_text("Merci {MOI} ❤ 73 !")
        b = a.bubbles[0]
        b.update(style="néon", fg="#ff3ec8", size="grande", anim=True, cx=0.3, cy=0.7, k=1.4)
        b["text"] = "Merci de {MOI} ❤ 73 !"
        self.assertTrue(a._save_bubble(b))
        saved = json.load(open(self.conf))["bub_saved"]                 # gardée dans les réglages
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["style"], "néon")
        a.bubbles.clear()
        ed.add_saved_bubble(a._saved_bubbles()[0])
        n = a.bubbles[0]
        self.assertEqual(n["text"], "Merci de RK1AT ❤ 73 !")              # {MOI} remplacé
        for k, v in (("style", "néon"), ("fg", "#ff3ec8"), ("size", "grande"), ("anim", True),
                     ("cx", 0.3), ("cy", 0.7), ("k", 1.4)):
            self.assertEqual(n[k], v)
        a.prepare(sync=True)
        self.assertIsNotNone(a.tx)

    def test_meme_texte_remplace_et_limite(self):
        a = self.a
        a.conf["bub_saved"] = []
        a._save_bubble({"text": "CQ", "style": "parole", "fg": "#000000"})
        a._save_bubble({"text": "CQ", "style": "parole", "fg": "#ff0000"})   # même bulle : remplacée
        a._save_bubble({"text": "CQ", "style": "bandeau", "speed": "lente"})  # autre style : en plus
        self.assertEqual(len(a._saved_bubbles()), 2)
        self.assertEqual(a._saved_bubbles()[0]["fg"], "#ff0000")
        self.assertFalse(a._save_bubble({"text": "  ", "style": "parole"}))   # vide : rien
        for i in range(40):
            a._save_bubble({"text": f"n{i}", "style": "parole"})
        self.assertEqual(len(a._saved_bubbles()), a.SAVED_BUBBLES_MAX)
        self.assertEqual(a._saved_bubbles()[-1]["text"], "n39")

    def test_reglages_abimes(self):
        a = self.a
        a.conf["bub_saved"] = [None, "x", {"style": "cri"}, {"text": "ok", "style": "cri"}]
        self.assertEqual([d["text"] for d in a._saved_bubbles()], ["ok"])
        a.conf["bub_saved"] = "pas une liste"
        self.assertEqual(a._saved_bubbles(), [])

    def test_menu_clic_droit(self):
        a, ed = self.a, self.ed
        a._save_bubble({"text": "73 !", "style": "cartouche"})
        ed.add_text("autre")
        ox, oy, dw, dh = self.box()
        import tkinter as tk
        posted = {}
        orig = tk.Menu.tk_popup
        tk.Menu.tk_popup = lambda m, x, y, *r: posted.setdefault("m", m)
        try:
            ed.menu(E(ox + dw // 2, oy + dh // 2))
        finally:
            tk.Menu.tk_popup = orig
        m = posted["m"]
        labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) != "separator"]
        self.assertIn("Ajouter une bulle enregistrée", labels)
        self.assertIn("Enregistrer cette bulle (avec son style)", labels)

    def test_fenetre_bulles_menu_phrases(self):
        """Fenêtre « Bulles… » : menu Phrases ▾ -> bulle enregistrée remise, et enregistrement."""
        import tkinter as tk
        from tkinter import ttk
        a = self.a
        a.conf["bub_saved"] = []
        a._save_bubble({"text": "QSL ? 73", "style": "cri", "bg": "#ffee00", "cx": 0.2, "cy": 0.2})
        a.bubbles.clear()
        a.bubble_dialog()
        a.update()
        wins = [w for w in a.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]

        def find(w):
            for c in w.winfo_children():
                if isinstance(c, ttk.Menubutton) and "▾" in str(c.cget("text")):
                    return c
                r = find(c)
                if r is not None:
                    return r
        mb = next(m for m in (find(w) for w in wins) if m is not None)
        menu = mb.nametowidget(mb.cget("menu"))
        menu.tk.eval(menu.cget("postcommand"))
        labels = [menu.entrycget(i, "label") if menu.type(i) != "separator" else "-"
                  for i in range(menu.index("end") + 1)]
        self.assertTrue(labels[0].startswith("★ QSL ? 73"))
        menu.invoke(0)                                             # remet la bulle enregistrée
        self.assertEqual(len(a.bubbles), 1)
        self.assertEqual((a.bubbles[0]["style"], a.bubbles[0]["bg"]), ("cri", "#ffee00"))
        a.bubbles[0]["fg"] = "#0000ff"
        menu.invoke(labels.index("Enregistrer cette bulle (avec son style)"))
        self.assertEqual(a._saved_bubbles()[0]["fg"], "#0000ff")  # même texte et style : remplacée
        self.assertEqual(len(a._saved_bubbles()), 1)
        for w in wins:
            w.destroy()


if __name__ == "__main__":
    unittest.main()
