"""1.24 (demande de VK6NJP) : commandes CAT personnalisées, comme EasyPal."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import radio  # noqa: E402


class Parse(unittest.TestCase):
    def test_formes(self):
        self.assertEqual(radio.parse_cmd("\\$FEFE5EE0140B0000FD\\"), bytes.fromhex("FEFE5EE0140B0000FD"))
        self.assertEqual(radio.parse_cmd("FE FE 5E E0 1C 00 01 FD"), bytes.fromhex("FEFE5EE01C0001FD"))
        self.assertEqual(radio.parse_cmd("TX1;"), b"TX1;")
        self.assertEqual(radio.parse_cmd("RX;|TX0;"), b"RX;TX0;")
        self.assertEqual(radio.parse_cmd("AB\\r"), b"AB\r")
        self.assertIsNone(radio.parse_cmd("   "))

    def test_plusieurs_comme_easypal(self):
        # 1.35 (VK6NJP) : plusieurs commandes à la suite dans une case, comme dans EasyPal
        s = "\\$FEFE94E0140B0000FD\\$FEFE94E01A060101FD\\$FEFE94E0164501FD\\"
        self.assertEqual(radio.parse_cmds(s), [bytes.fromhex("FEFE94E0140B0000FD"),
                                               bytes.fromhex("FEFE94E01A060101FD"),
                                               bytes.fromhex("FEFE94E0164501FD")])
        self.assertEqual(radio.parse_cmd(s), bytes.fromhex("FEFE94E0140B0000FDFEFE94E01A060101FDFEFE94E0164501FD"))
        # sans « \ » final, ou avec des espaces
        self.assertEqual(len(radio.parse_cmds("\\$FEFE94E0140B0000FD\\$FEFE94E01A060101FD")), 2)
        self.assertEqual(len(radio.parse_cmds(" \\$FEFE94E0140B0000FD\\ \\$FEFE94E01A060101FD\\ ")), 2)
        self.assertEqual(radio.parse_cmds("RX;|TX0;"), [b"RX;", b"TX0;"])
        self.assertEqual(radio.parse_cmds(""), [])

    def test_liste_et_description(self):
        self.assertIn("custom", radio.rig_keys())
        self.assertEqual(radio.rig_entry("custom")["kind"], "custom")
        cfg = dict(radio.DEFAULTS, rig="custom", port="/dev/ttyUSB0", baud=19200, ptt="CAT")
        self.assertIn("/dev/ttyUSB0 19200", radio.describe(cfg))


@unittest.skipIf(sys.platform.startswith("win"), "pseudo-terminal : Linux")
class PortSerie(unittest.TestCase):
    def test_sequence_comme_easypal(self):
        import pty
        master, slave = pty.openpty()
        os.set_blocking(master, False)
        port = os.ttyname(slave)
        cfg = dict(radio.DEFAULTS, rig="custom", port=port, baud=9600, ptt="CAT", cmd_delay=10,
                   cmd_init1="\\$FEFE5EE0140B0000FD\\", cmd_ptt_on="FEFE5EE01C0001FD",
                   cmd_ptt_off="FEFE5EE01C0000FD", cmd_exit1="\\$FEFE5EE0140B0140FD\\")

        def read():
            time.sleep(0.15)
            try:
                return os.read(master, 4096)
            except BlockingIOError:
                return b""
        rig = radio.make_rig(cfg)
        self.assertFalse(rig.reads_freq)
        self.assertIsNone(rig.freq())
        self.assertEqual(read(), bytes.fromhex("FEFE5EE0140B0000FD"))      # départ, à l'ouverture
        p = radio.Ptt(cfg, rig)
        p.tx()
        self.assertEqual(read(), bytes.fromhex("FEFE5EE01C0001FD"))
        p.rx()
        self.assertEqual(read(), bytes.fromhex("FEFE5EE01C0000FD"))
        rig.close()
        self.assertEqual(read(), bytes.fromhex("FEFE5EE0140B0140FD"))      # sortie, à la fermeture
        os.close(master)
        os.close(slave)

    def test_plusieurs_avec_delai(self):
        import pty
        master, slave = pty.openpty()
        os.set_blocking(master, False)
        cfg = dict(radio.DEFAULTS, rig="custom", port=os.ttyname(slave), baud=9600, ptt="CAT",
                   cmd_delay=200, cmd_init1="\\$FEFE94E0140B0000FD\\$FEFE94E01A060101FD\\")
        t0 = time.time()
        rig = radio.make_rig(cfg)
        self.assertGreaterEqual(time.time() - t0, 0.35)                  # délai après chacune
        time.sleep(0.1)
        self.assertEqual(os.read(master, 4096), bytes.fromhex("FEFE94E0140B0000FDFEFE94E01A060101FD"))
        rig.close()
        os.close(master)
        os.close(slave)

    def test_ptt_vide(self):
        import pty
        master, slave = pty.openpty()
        cfg = dict(radio.DEFAULTS, rig="custom", port=os.ttyname(slave), ptt="CAT")
        rig = radio.make_rig(cfg)
        with self.assertRaises(RuntimeError):
            rig.ptt(True)
        rig.close()
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    unittest.main()
