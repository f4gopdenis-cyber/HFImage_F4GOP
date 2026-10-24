"""1.31 : carte des stations plus lisible (couleurs selon le report, étiquettes sans chevauchement)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import stationmap as sm  # noqa: E402
import protocol  # noqa: E402


class Carte(unittest.TestCase):
    def test_couleurs(self):
        self.assertEqual(sm.report_color(11), sm.REPORT_COLORS[0][1])
        self.assertEqual(sm.report_color(0), sm.REPORT_COLORS[1][1])
        self.assertEqual(sm.report_color(-7), sm.REPORT_COLORS[2][1])
        self.assertEqual(sm.report_color(-12), sm.REPORT_COLORS[3][1])
        self.assertEqual(sm.report_color(None), sm.NO_REPORT)

    def test_etiquettes_sans_chevauchement(self):
        locs = {"G4XGT": "IO92JL", "M6MGN": "IO91AK", "G7VQV": "IO90QS", "M7WUV": "IO90IR", "2E1HOL": "IO83RL",
                "F1SZC": "IN95UJ", "F1UGC": "IN94RT", "F5BRF": "IN94QR", "14FR79": "IN96VC"}
        me = {"call": "F4GOP", "pos": protocol.locator_to_latlon("IN98QR")}
        st = [{"call": c, "pos": protocol.locator_to_latlon(l), "ok": True, "rep": 3} for c, l in locs.items()]
        v = sm.fit_view([s["pos"] for s in st] + [me["pos"]], 900, 600)
        sm.render(v, st, me)
        boxes = [s["_hit"][:4] for s in st + [me]]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertTrue(a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3], (a, b))
        # chaque étiquette reste près de son point
        for s in st:
            bx0, by0, bx1, by1, px, py = s["_hit"]
            cx, cy = min(max(px, bx0), bx1), min(max(py, by0), by1)
            self.assertLess(((cx - px) ** 2 + (cy - py) ** 2) ** 0.5, 120)


    def test_villes_cedent_la_place(self):
        # 1.39 : un nom de ville qui tomberait sous une étiquette de station n'est pas écrit
        man = next(c for c in sm.load()["cities"] if c[0] == "Manchester")
        pos = (man[2] / 100, man[1] / 100)
        me = {"call": "F4GOP", "pos": protocol.locator_to_latlon("IN98QR")}
        v = sm.View(pos[1], pos[0], 6, 600, 400)
        self.assertIn("Manchester", sm.render(v, [], me).info.get("cities", []))
        avec = sm.render(v, [{"call": "M0GRY", "pos": pos, "ok": True, "rep": -4}], me)
        self.assertNotIn("Manchester", avec.info.get("cities", []))
        self.assertTrue(avec.info.get("cities"))                     # les autres villes restent

    def test_espace_entre_etiquettes(self):
        items = [(100, 100, 60, 17), (100, 100, 60, 17), (100, 100, 60, 17)]
        pl = sm._place_labels(items, 400, 300, avoid=[(100, 100)])
        boxes = [(x, y, x + 60, y + 17) for x, y in pl]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertTrue(a[2] + sm.LABEL_GAP <= b[0] or a[0] - sm.LABEL_GAP >= b[2]
                                or a[3] + sm.LABEL_GAP <= b[1] or a[1] - sm.LABEL_GAP >= b[3], (a, b))

    def test_copier_la_carte(self):
        import tkinter as tk
        from unittest import mock
        import clip
        try:
            root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        try:
            me = {"call": "F4GOP", "pos": protocol.locator_to_latlon("IN98QR")}
            st = [{"call": "G4GIM", "pos": protocol.locator_to_latlon("IO82UK"), "ok": True, "rep": 1}]
            w = sm.MapWindow(root, lambda: (me, st))
            w.win.geometry("600x400")
            root.update()
            w.set_view("*")
            got = []
            with mock.patch.object(clip, "copy_image", lambda im: got.append(im.size)):
                self.assertTrue(w.copy())
            self.assertEqual(got, [w._img.size])
            self.assertIn("Ctrl+V", w.info.cget("text"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
