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
        cfg = dict(radio.DEFAULTS, rig="custom", port=port, baud=9600, ptt="CAT", cmd_delay=10, cmd_when="open",
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
                   cmd_delay=200, cmd_when="open", cmd_init1="\\$FEFE94E0140B0000FD\\$FEFE94E01A060101FD\\")
        t0 = time.time()
        rig = radio.make_rig(cfg)
        self.assertGreaterEqual(time.time() - t0, 0.35)                  # délai après chacune
        time.sleep(0.1)
        self.assertEqual(os.read(master, 4096), bytes.fromhex("FEFE94E0140B0000FDFEFE94E01A060101FD"))
        rig.close()
        os.close(master)
        os.close(slave)

    def _pty(self):
        import pty
        master, slave = pty.openpty()
        os.set_blocking(master, False)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)

        def read():
            time.sleep(0.15)
            try:
                return os.read(master, 4096)
            except BlockingIOError:
                return b""
        return os.ttyname(slave), read

    def test_a_chaque_emission(self):
        # 1.36 (VK6NJP) : comme EasyPal, départ avant chaque émission, sortie après
        port, read = self._pty()
        self.assertEqual(radio.DEFAULTS["cmd_when"], "tx")
        cfg = dict(radio.DEFAULTS, rig="custom", port=port, baud=9600, ptt="CAT", cmd_delay=10,
                   cmd_init1="\\$FEFE94E01A060101FD\\", cmd_ptt_on="FEFE94E01C0001FD",
                   cmd_ptt_off="FEFE94E01C0000FD", cmd_exit1="\\$FEFE94E01A060000FD\\")
        rig = radio.make_rig(cfg)
        self.assertEqual(read(), b"")                                      # rien à l'ouverture
        p = radio.Ptt(cfg, rig)
        for _ in range(2):                                                 # à chaque émission
            p.tx()
            self.assertEqual(read(), bytes.fromhex("FEFE94E01A060101FD" "FEFE94E01C0001FD"))
            p.rx()
            self.assertEqual(read(), bytes.fromhex("FEFE94E01C0000FD" "FEFE94E01A060000FD"))
        p.rx()                                                             # pas de sortie en double
        self.assertEqual(read(), bytes.fromhex("FEFE94E01C0000FD"))
        rig.close()
        self.assertEqual(read(), b"")                                      # rien à la fermeture

    def test_a_chaque_emission_sans_ptt_cat(self):
        # PTT sans CAT (VOX, RTS…) : les chaînes de départ / sortie partent quand même
        port, read = self._pty()
        cfg = dict(radio.DEFAULTS, rig="custom", port=port, baud=9600, ptt="VOX", cmd_delay=10,
                   cmd_init1="FEFE94E01A060101FD", cmd_exit1="FEFE94E01A060000FD")
        rig = radio.make_rig(cfg)
        p = radio.Ptt(cfg, rig)
        p.tx()
        self.assertEqual(read(), bytes.fromhex("FEFE94E01A060101FD"))
        rig.close()                                                        # fermé en émission
        self.assertEqual(read(), bytes.fromhex("FEFE94E01A060000FD"))

    def test_frequence_icom(self):
        # 1.37 (VK6NJP) : commandes Icom CI-V -> HFImage change aussi la fréquence (commande 05)
        port, read = self._pty()
        cfg = dict(radio.DEFAULTS, rig="custom", port=port, baud=9600, ptt="CAT", cmd_delay=0,
                   cmd_init1="\\$FEFE94E01A060101FD\\", cmd_ptt_on="FEFE94E01C0001FD",
                   cmd_ptt_off="FEFE94E01C0000FD")
        rig = radio.make_rig(cfg)
        self.assertTrue(rig.can_qsy)
        self.assertIsNone(rig.freq())
        msg = rig.qsy(7058000, "LSB")
        self.assertEqual(read(), bytes.fromhex("FEFE94E005" "0080050700" "FD"))
        self.assertIn("7.058", msg)
        self.assertEqual(rig.freq(), 7058000)
        rig.qsy(14230000, "USB")
        self.assertEqual(read(), bytes.fromhex("FEFE94E005" "0000231400" "FD"))
        rig.close()

    def test_frequence_texte_impossible(self):
        port, read = self._pty()
        cfg = dict(radio.DEFAULTS, rig="custom", port=port, ptt="CAT", cmd_ptt_on="TX1;", cmd_ptt_off="RX;")
        rig = radio.make_rig(cfg)
        self.assertFalse(rig.can_qsy)
        with self.assertRaises(RuntimeError):
            rig.set_freq(7058000)
        self.assertEqual(read(), b"")
        rig.close()

    def test_messages_traduits(self):
        import i18n
        i18n.set_lang("en")
        try:
            self.assertEqual(i18n.tr("ce pilote ne change pas la fréquence"), "this driver cannot change the frequency")
            self.assertEqual(i18n.tr("Commandes CAT personnalisées : changez la fréquence sur le poste."),
                             "Custom CAT commands: change the frequency on the radio.")
        finally:
            i18n.set_lang("fr")

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
