"""2.55 (Keith Woodley) : messages envoyés (TX) et reçus (RX) dans le même cadre, et dans le journal."""
import gc
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class Messages(unittest.TestCase):
    def test_tx_rx(self):
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "VK6WK", "licence_ok": "1.0", "lang": "en", "net_on": False}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                logs = []
                orig = a.log
                with mock.patch.object(a, "log", side_effect=lambda m: (logs.append(app.tr(m)), orig(m))):
                    a._show_message("VK3AML", "Hello Keith, conditions are poor tonight")
                    long = "Thanks Chris, " + "copied all your messages. " * 8
                    a._msg_sent(0x1234, long, "DATAC3")
                    a._show_message("VK3AML", "73")
                txt = a.msgbox.get("1.0", "end-1c").splitlines()
                self.assertEqual(len(txt), 3)
                self.assertTrue(txt[0].startswith("RX [") and txt[0].endswith("VK3AML : 73"))
                self.assertTrue(txt[1].startswith("TX [") and "VK6WK : " + long.strip() in txt[1])
                self.assertTrue(txt[2].startswith("RX [") and "conditions are poor" in txt[2])
                self.assertIn("tx", a.msgbox.tag_names("2.0"))
                self.assertTrue(any(m.startswith("Message sent (DATAC3): Thanks Chris") for m in logs))
            finally:
                a.destroy()
                import i18n
                i18n.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
