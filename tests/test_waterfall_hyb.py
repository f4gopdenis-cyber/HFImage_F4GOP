"""2.34 (VK6NJP) : pendant une annonce hybride, le waterfall affiche « DATAC3 HYB »."""
import os
import sys
import tkinter as tk
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import waterfall  # noqa: E402


class Hyb(unittest.TestCase):
    def test_etiquette(self):
        try:
            root = tk.Tk()
        except tk.TclError as e:
            raise unittest.SkipTest(str(e))
        try:
            wf = waterfall.Waterfall(root)
            wf.pack(fill="both", expand=True)
            root.geometry("800x200")
            root.update()
            texts = lambda: [wf.itemcget(i, "text") for i in wf.find_withtag("band") if wf.type(i) == "text"]
            wf.mark_mode("DATAC3", "DATAC3 HYB")
            self.assertEqual(texts(), ["DATAC3 HYB"])
            wf.mark_mode("DATAC1")
            self.assertEqual(texts(), ["DATAC1"])
        finally:
            root.destroy()
