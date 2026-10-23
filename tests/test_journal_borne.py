"""1.22 : le journal à l'écran se vide tout seul (300 dernières lignes)."""
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Journal(unittest.TestCase):
    def test_borne(self):
        try:
            import app
            import tkinter as tk
            root = tk.Tk()
        except Exception as e:
            self.skipTest(str(e))
        box = tk.Text(root)
        with tempfile.TemporaryDirectory() as d:
            s = types.SimpleNamespace(logbox=box, LOG_KEEP=app.App.LOG_KEEP, written=[])
            s._journal = s.written.append
            with mock.patch.object(app, "tr", lambda m: m):
                for i in range(1000):
                    app.App.log(s, f"ligne {i}")
        n = int(box.index("end-1c").split(".")[0])
        self.assertLessEqual(n, app.App.LOG_KEEP + 101)
        self.assertIn("ligne 999", box.get("end-2l", "end"))
        self.assertNotIn("ligne 0\n", box.get("1.0", "end"))
        self.assertEqual(len(s.written), 1000)               # tout reste dans le fichier journal
        root.destroy()


if __name__ == "__main__":
    unittest.main()
