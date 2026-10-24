"""1.40 (demande de SWLPete, via VK6NJP) : la liste des stations et Rx Ok ne « sautent » plus à chaque
mise à jour : même station sélectionnée, même partie de la liste affichée, rien de réécrit si rien
n'a changé."""
import gc
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class ListeStable(unittest.TestCase):
    def setUp(self):
        gc.collect()
        import tkinter as tk
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        self.sync = lambda lst, k, r: app.App._sync_list(lst, k, r)
        self.lst = tk.Listbox(self.root, height=5)
        self.lst.pack()
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.root = None
        gc.collect()

    def rows(self, keys, freq="7.058"):
        return [(f"{k:<8} {freq}", "#062e06") for k in keys]

    def test_rien_ne_change(self):
        keys = [f"F{i}ABC" for i in range(20)]
        self.sync(self.lst, keys, self.rows(keys))
        calls = []
        orig = self.lst.delete
        self.lst.delete = lambda *a: (calls.append(a), orig(*a))
        self.sync(self.lst, keys, self.rows(keys))
        self.assertEqual(calls, [])

    def test_position_et_selection_gardees(self):
        keys = [f"F{i:02d}ABC" for i in range(30)]
        self.sync(self.lst, keys, self.rows(keys))
        self.lst.yview(15)                               # on regarde le bas de la liste
        self.lst.selection_set(17)
        self.root.update()
        self.assertEqual(self.lst.nearest(0), 15)
        # une station arrive en haut de la liste, une autre change de fréquence
        keys2 = ["DL1AAA"] + keys
        rows2 = self.rows(keys2)
        rows2[5] = (rows2[5][0].replace("7.058", "14.230"), "#c01818")
        self.sync(self.lst, keys2, rows2)
        self.root.update()
        self.assertEqual(keys2[self.lst.nearest(0)], "F15ABC")       # même station en haut
        self.assertEqual([keys2[i] for i in self.lst.curselection()], ["F17ABC"])
        self.assertEqual(self.lst.get(5), rows2[5][0])

    def test_seule_la_ligne_changee(self):
        keys = [f"F{i:02d}ABC" for i in range(10)]
        self.sync(self.lst, keys, self.rows(keys))
        self.lst.selection_set(3)
        rows2 = self.rows(keys)
        rows2[3] = (rows2[3][0] + " HYB", "#1f4fbf")
        calls = []
        orig = self.lst.delete
        self.lst.delete = lambda *a: (calls.append(a), orig(*a))
        self.sync(self.lst, keys, rows2)
        self.assertEqual(calls, [(3,)])
        self.assertEqual(self.lst.get(3), rows2[3][0])
        self.assertEqual(self.lst.curselection(), (3,))
        self.assertEqual(str(self.lst.itemcget(3, "fg")), "#1f4fbf")

    def test_station_partie(self):
        keys = [f"F{i:02d}ABC" for i in range(30)]
        self.sync(self.lst, keys, self.rows(keys))
        self.lst.yview(10)
        self.root.update()
        keys2 = [k for k in keys if k != "F10ABC"]        # la station du haut de l'affichage s'en va
        self.sync(self.lst, keys2, self.rows(keys2))
        self.root.update()
        self.assertLessEqual(abs(self.lst.nearest(0) - 10), 1)       # la liste ne remonte pas en haut


    def test_jamais_decalee_a_droite(self):
        # 1.43 : liste décalée d'un cran (molette / pavé tactile) -> « 4VD274 » pour « 14VD274 »
        import app
        lst = self.lst
        lst.configure(width=6, xscrollcommand=app.App._no_xscroll(lst))
        keys = ["14VD274", "2E1HOL", "DL7VOE"]
        rows = [(f"{k:<8} 7.058 HYB", None) for k in keys]
        self.sync(lst, keys, rows)
        self.root.update()
        lst.xview_scroll(1, "units")                     # décalage horizontal
        self.root.update()
        self.root.update()
        self.assertEqual(lst.xview()[0], 0.0)
        lst.xview_moveto(0.3)
        self.sync(lst, keys, rows)                       # rien n'a changé : remise au début quand même
        self.root.update()
        self.assertEqual(lst.xview()[0], 0.0)


if __name__ == "__main__":
    unittest.main()
