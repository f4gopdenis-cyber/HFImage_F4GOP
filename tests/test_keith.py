"""2.47 (signalé par Keith Woodley, WASSTV, sous Linux) : traductions, listes, messages, dépôt FTP,
coller / glisser une image, dossier des images, texte waterfall."""
import gc
import io
import json
import os
import socket
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PIL import Image  # noqa: E402


class SansFenetre(unittest.TestCase):
    def test_traduction_avec_espaces(self):
        import i18n
        old = i18n.get_lang()
        try:
            i18n.set_lang("en")
            self.assertEqual(i18n.tr("   ↳ message ci-dessous envoyé par VK6ATI"), "   ↳ message below sent by VK6ATI")
        finally:
            i18n.set_lang(old)

    def test_mymemory_meme_langue(self):
        import translate
        bad = {"responseData": {"translatedText": "PLEASE SELECT TWO DISTINCT LANGUAGES"}, "responseStatus": 403}
        with mock.patch.object(translate, "_get", return_value=bad):
            self.assertEqual(translate._mymemory("Hello all, 73", "en"), ("", ""))
            self.assertIsNone(translate.translate("Hello all, 73 from VK6", "en", services=(translate._mymemory,)))

    def test_depot_ftp_nouvel_essai(self):
        import hybrid
        calls = []

        class FakeFTP:
            def __init__(self):
                self.n = len(calls)

            def storbinary(self, cmd, f, blocksize=8192, callback=None):
                calls.append(cmd)
                if len(calls) == 1:
                    raise socket.timeout("timed out")
                callback(f.read())

            def quit(self):
                pass

        logs = []
        with mock.patch.object(hybrid, "_ftp_connect", lambda cfg, timeout=20: FakeFTP()), \
                mock.patch.object(hybrid, "_ftp_cd", lambda ftp, d: None):
            ftp = hybrid.store({"host": "h"}, "", "a.jpg", b"x" * 1000, log=logs.append)
        self.assertEqual(len(calls), 2)                      # coupé, puis réussi au 2e essai
        self.assertTrue(any("nouvel essai" in m for m in logs))
        self.assertIsInstance(ftp, FakeFTP)
        self.assertEqual(hybrid.UPLOAD_TIMEOUT, 60)


class AvecFenetre(unittest.TestCase):
    def setUp(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        self.appmod = app
        self.d = tempfile.mkdtemp()
        conf = os.path.join(self.d, "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6KW", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        gc.collect()
        self.p = mock.patch.object(app, "CONF_PATH", conf)
        self.p.start()
        try:
            self.a = app.App()
        except Exception as e:
            self.p.stop()
            raise unittest.SkipTest(str(e))
        self.a.update()

    def tearDown(self):
        self.a.destroy()
        self.p.stop()
        import i18n
        i18n.set_lang("fr")

    def test_hauteur_des_lignes(self):
        import tkinter.font as tkfont
        from tkinter import ttk
        ls = tkfont.nametofont("TkDefaultFont").metrics("linespace")
        rh = int(ttk.Style(self.a).lookup("Treeview", "rowheight") or 0)
        self.assertGreaterEqual(rh, ls + 6)

    def test_deuxieme_clic_pendant_emission(self):
        a = self.a
        a.tx_busy = True
        with mock.patch.object(self.appmod.messagebox, "showinfo") as info, \
                mock.patch.object(a, "_send_text_now") as send:
            a.send_text()
            info.assert_not_called()
            send.assert_not_called()

    def test_messages_devant(self):
        import tkinter.messagebox as mb
        self.assertTrue(getattr(mb, "_hf_front", False))
        with mock.patch("tkinter.messagebox._show", return_value="ok") as show:
            mb.showinfo("HFImage", "test")
        self.assertIsNotNone(show.call_args.kwargs.get("parent"))

    def test_message_envoye_en_entier(self):
        a = self.a
        long = "This is a long message from VK6KW to the WASSTV net, " * 4
        a._msg_sent(1234, long, "DATAC3")
        a._msg_ack(1234, "VK6ATI", 5, "radio")
        a._msg_ack(1234, "VK6NJP", 3, "radio")
        box = a.msgbox.get("1.0", "end")
        self.assertNotIn("WASSTV net", box)                   # l'accusé ne répète plus le texte coupé
        self.assertIn("VK6ATI", box)
        tv = a.tv_sent
        first = tv.get_children()[0]
        tv.focus(first)
        tv.selection_set(first)
        w = a._sent_msg_show()
        self.assertIsNotNone(w)
        import tkinter as tk
        texts = [c for c in w.winfo_children()[0].winfo_children() if isinstance(c, tk.Text)]
        self.assertIn(long.strip(), texts[0].get("1.0", "end"))
        w.destroy()

    def test_coller_un_fichier_copie_linux(self):
        a = self.a
        p = os.path.join(self.d, "photo.png")
        Image.new("RGB", (40, 30), (10, 20, 30)).save(p)
        a.clipboard_clear()
        a.clipboard_append("file://" + p)
        with mock.patch("PIL.ImageGrab.grabclipboard", return_value=None), \
                mock.patch.object(a, "load_image") as load:
            a.paste_image()
        load.assert_called_once_with(p)

    def test_lien_glisse_depuis_le_navigateur(self):
        a = self.a
        with mock.patch.object(a, "_fetch_image_url") as fetch:
            a._dropped(["https://example.org/photo.jpg"])
        fetch.assert_called_once_with("https://example.org/photo.jpg")
        buf = io.BytesIO()
        Image.new("RGB", (32, 24), (200, 10, 10)).save(buf, "PNG")

        class R:
            def __init__(self):
                self.b = io.BytesIO(buf.getvalue())

            def read(self, n):
                return self.b.read(n)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch("urllib.request.urlopen", return_value=R()), mock.patch.object(a, "load_image") as load:
            a._fetch_image_url("https://example.org/photo.png")
            end = time.time() + 3
            while time.time() < end and not load.called:
                a.update()
                time.sleep(0.02)
        load.assert_called_once()

    def test_dernier_dossier(self):
        a = self.a
        p = os.path.join(self.d, "x.png")
        Image.new("RGB", (8, 8)).save(p)
        with mock.patch.object(self.appmod.filedialog, "askopenfilename", return_value=p) as ask, \
                mock.patch.object(a, "load_image"):
            a.open_image()
            a.open_image()
        self.assertEqual(ask.call_args.kwargs["initialdir"], self.d)

    def test_waterfall_enregistrer_sous(self):
        a = self.a
        out = os.path.join(self.d, "mon_texte.wav")
        with mock.patch.object(a, "_wft_bitmap", return_value=__import__("numpy").ones((4, 8))), \
                mock.patch.object(self.appmod.filedialog, "asksaveasfilename", return_value=out), \
                mock.patch.object(self.appmod.messagebox, "askyesno", return_value=False):
            a.wft_save()
        self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
