"""Version 1.59 : ports COM et Icom (IC-7300MK2, IC-7610), PTT, « DATA auto »."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import audio  # noqa: E402
import radio  # noqa: E402
import riglist  # noqa: E402


class FakeSerial:
    """serial.Serial factice : note l'état des lignes au moment de l'ouverture."""
    opened = []
    fail = None

    def __init__(self, port=None, baud=9600, timeout=None, write_timeout=None):
        self.port, self.baudrate = port, baud
        self.dtr = self.rts = True                    # comme pyserial : lignes hautes par défaut
        self.xonxoff = self.rtscts = False
        self.bytesize = self.stopbits = None
        self.is_open = False
        self.written = []
        if port is not None:
            self.open()

    def open(self):
        if FakeSerial.fail:
            import serial
            raise serial.SerialException(FakeSerial.fail)
        self.is_open = True
        FakeSerial.opened.append((self.port, self.dtr, self.rts))

    def write(self, b):
        self.written.append(b)

    def flush(self):
        pass

    def close(self):
        self.is_open = False


class Base(unittest.TestCase):
    def setUp(self):
        try:
            import serial
        except ImportError as e:
            self.skipTest(str(e))
        FakeSerial.opened, FakeSerial.fail = [], None
        p = mock.patch.object(serial, "Serial", FakeSerial)
        p.start()
        self.addCleanup(p.stop)

    @staticmethod
    def cfg(**kw):
        c = dict(radio.DEFAULTS)
        c.update(kw)
        return c


class Ports(Base):
    def test_ptt_rts_meme_port_ligne_basse_des_l_ouverture(self):
        # avant : la ligne RTS montait à l'ouverture -> émission dès le lancement du programme
        radio.open_port(self.cfg(rig="custom", port="COM4", ptt="RTS"))
        self.assertEqual(FakeSerial.opened, [("COM4", True, False)])

    def test_ptt_dtr_autre_port_cat_inchange(self):
        radio.open_port(self.cfg(rig="custom", port="COM4", ptt="DTR", ptt_port="COM9"))
        self.assertEqual(FakeSerial.opened, [("COM4", True, True)])

    def test_lignes_forcees(self):
        radio.open_port(self.cfg(rig="custom", port="COM4", dtr="low", rts="high"))
        self.assertEqual(FakeSerial.opened, [("COM4", False, True)])

    def test_port_ptt_separe_ouvert_lignes_basses(self):
        p = radio.Ptt(self.cfg(rig="none", ptt="RTS", ptt_port="COM7"), None)
        self.assertEqual(FakeSerial.opened, [("COM7", False, False)])
        p.tx()
        self.assertTrue(p.ser.rts)
        self.assertIsNone(p.close())

    def test_com13_n_est_pas_occupe(self):
        # « 13 » dans le message faisait croire à un port occupé
        FakeSerial.fail = "could not open port 'COM13': FileNotFoundError(2, 'Le fichier spécifié est introuvable.')"
        with self.assertRaises(RuntimeError) as cm:
            audio.open_serial("COM13", 9600)
        self.assertIn("n'existe pas", str(cm.exception))

    def test_port_occupe(self):
        FakeSerial.fail = "could not open port 'COM5': PermissionError(13, 'Accès refusé.', None, 5)"
        with self.assertRaises(RuntimeError) as cm:
            audio.open_serial("COM5", 9600)
        self.assertIn("déjà utilisé", str(cm.exception))
        self.assertIn("IC-7610", str(cm.exception))


class PttRetour(unittest.TestCase):
    def test_retour_reception_repete(self):
        calls = []

        class Rig(radio.RigBase):
            def ptt(self, on, rear=True):
                calls.append(on)
                if not on and calls.count(False) < 3:
                    raise RuntimeError("le poste ne répond pas")
        with mock.patch.object(radio.time, "sleep", lambda s: None):
            p = radio.Ptt({"rig": "hamlib:3073", "ptt": "CAT", "tx_audio": "rear"}, Rig())
            p.tx()
            self.assertIsNone(p.close())
        self.assertEqual(calls, [True, False, False, False])

    def test_echec_signale(self):
        class Rig(radio.RigBase):
            def ptt(self, on, rear=True):
                if not on:
                    raise RuntimeError("liaison perdue")
        with mock.patch.object(radio.time, "sleep", lambda s: None):
            p = radio.Ptt({"rig": "hamlib:3073", "ptt": "CAT", "tx_audio": "rear"}, Rig())
            self.assertIn("liaison perdue", str(p.close()))


class Icom(unittest.TestCase):
    def test_ic7300mk2_dans_la_liste(self):
        self.assertEqual(riglist.HAMLIB_VERSION, "4.7.2")
        self.assertEqual(radio.rig_label("hamlib:3094"), "Icom IC-7300MK2")
        self.assertEqual(radio.rig_label("hamlib:3078"), "Icom IC-7610")
        self.assertEqual(radio.rig_entry("hamlib:3094")["kind"], "hamlib")

    def test_adresse_civ(self):
        for t, v in (("B6", 0xB6), ("b6h", 0xB6), ("0x94", 0x94), ("", None), ("ZZ", None), ("FE", None)):
            self.assertEqual(radio.civ_addr({"civ": t}), v, t)

    def test_conseil_icom(self):
        self.assertIn("B6h", radio.icom_hint("Icom IC-7300MK2"))
        self.assertIn("98h", radio.icom_hint("Icom IC-7610"))
        self.assertIn("deux ports COM", radio.icom_hint("Icom IC-7610"))


class Rigctld(unittest.TestCase):
    """Ligne de commande de rigctld (sans le lancer vraiment)."""

    def start(self, cfg, model=3073, exits=()):
        runs = []

        class Proc:
            def __init__(self, args, **kw):
                runs.append(args)
                self.args, self.pid = args, 1
                self.returncode = 2 if args[2] in exits else None

            def poll(self):
                return self.returncode

            def kill(self):
                self.returncode = -9

            terminate = kill

            def wait(self, timeout=None):
                return self.returncode

        def fake_init(self, cfg, host, port, label):
            self.sock = None
        c = dict(radio.DEFAULTS)
        c.update(cfg)
        with mock.patch.object(radio, "find_rigctld", lambda: "/usr/bin/rigctld"), \
                mock.patch.object(radio.subprocess, "Popen", Proc), \
                mock.patch.object(radio.RigctlRig, "__init__", fake_init), \
                mock.patch.object(radio.RigctlRig, "freq", lambda self: 7100000), \
                mock.patch.object(radio.time, "sleep", lambda s: None), \
                mock.patch.object(radio, "_kill_with_us", lambda p: None), \
                mock.patch("builtins.open", mock.mock_open()):
            r = radio.HamlibRig(c, model, radio.rig_label(f"hamlib:{model}"))
        return r, runs

    def test_pas_de_ligne_forcee_sur_le_ptt(self):
        # Hamlib refuse de démarrer si RTS est forcé alors que le PTT passe par RTS
        _, runs = self.start({"port": "COM4", "rts": "low", "dtr": "low", "ptt": "RTS"})
        a = runs[-1]
        conf = next((x for x in a if x.startswith("--set-conf=")), "")
        self.assertNotIn("rts_state", conf)
        self.assertIn("dtr_state=OFF", conf)
        self.assertEqual(a[a.index("-P") + 1], "RTS")

    def test_rts_et_controle_materiel(self):
        _, runs = self.start({"port": "COM4", "rts": "high", "handshake": "hardware"})
        self.assertNotIn("rts_state", " ".join(runs[-1]))

    def test_adresse_civ_choisie(self):
        _, runs = self.start({"port": "COM4", "civ": "B6"})
        a = runs[-1]
        self.assertEqual(a[a.index("-c") + 1], "0xB6")

    def test_mk2_avec_hamlib_trop_ancien(self):
        # rigctld ne connaît pas le 3094 : relancé en IC-7300 à l'adresse B6h
        _, runs = self.start({"port": "COM4"}, model=3094, exits=("3094",))
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[1][2], "3073")
        self.assertEqual(runs[1][runs[1].index("-c") + 1], "0xB6")

    def test_mk2_avec_hamlib_recent(self):
        _, runs = self.start({"port": "COM4"}, model=3094)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0][2], "3094")
        self.assertNotIn("-c", runs[0])


class DataAuto(unittest.TestCase):
    """Bouton « DATA auto » : LSB -> LSB-DATA pour l'image, retour en LSB à la fin."""

    class Rig(radio.RigBase):
        def __init__(self, m="LSB"):
            self.m, self.cmds = m, []
            self.model = "TS-990S"

        def mode(self):
            return self.m

        def set_mode(self, which):
            self.cmds.append(which)
            self.m = ("LSB" if self.is_lsb(self.m) else "USB") + "-DATA1"
            return True, f"passé en {self.m}"

        def set_voice(self, side):
            self.cmds.append(side)
            self.m = side

    def stub(self, on=True):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        logs = []

        class Stub:
            conf = {"data_auto": on}
            log = staticmethod(logs.append)
            log_exc = staticmethod(lambda *a: logs.append(a))
            ui = staticmethod(lambda fn, *a: fn(*a))

            class _rig_kick:
                set = staticmethod(lambda: None)
        st = Stub()
        st.on = lambda r: app.App._data_auto_on(st, r, {"kind": "image"})
        st.off = lambda r, side: app.App._data_auto_off(st, r, side)
        return st, logs

    def test_lsb_aller_retour(self):
        st, logs = self.stub()
        r = self.Rig("LSB")
        side = st.on(r)
        self.assertEqual((side, r.m), ("LSB", "LSB-DATA1"))
        st.off(r, side)
        self.assertEqual(r.m, "LSB")
        self.assertTrue(all(isinstance(m, str) for m in logs))

    def test_usb(self):
        st, _ = self.stub()
        r = self.Rig("USB")
        st.off(r, st.on(r))
        self.assertEqual(r.cmds, ["data", "USB"])

    def test_deja_en_data_rien(self):
        st, _ = self.stub()
        r = self.Rig("USB-DATA1")
        st.off(r, st.on(r))
        self.assertEqual(r.cmds, [])

    def test_fm_ou_cw_rien(self):
        st, _ = self.stub()
        r = self.Rig("FM")
        st.off(r, st.on(r))
        self.assertEqual(r.cmds, [])

    def test_bouton_eteint(self):
        st, _ = self.stub(on=False)
        r = self.Rig("LSB")
        st.off(r, st.on(r))
        self.assertEqual(r.cmds, [])

    def test_kenwood_retour_phonie(self):
        sent = []
        k = radio.KenwoodRig.__new__(radio.KenwoodRig)
        k.write = sent.append
        with mock.patch.object(radio.time, "sleep", lambda s: None):
            k.query = lambda c: "SF000007058000C;"
            for model, want in (("TS-990S", ["OM01;"]), ("TS-890S", ["SF000007058000" + "1;"]),
                                ("TS-590SG", ["MD1;", "DA0;"])):
                sent.clear()
                k.model = model
                k.set_voice("LSB")
                self.assertEqual(sent, want, model)


class ListePorts(unittest.TestCase):
    def test_libelles(self):
        try:
            import radiodlg
        except ImportError as e:
            self.skipTest(str(e))
        lab = radiodlg.port_label("COM5", "Silicon Labs Dual CP2105 USB to UART Bridge: Enhanced COM Port (COM5)")
        self.assertEqual(lab, "COM5 — Silicon Labs Dual CP2105 USB to UART Bridge: Enhanced COM Port")
        self.assertEqual(radiodlg.port_name(lab), "COM5")
        self.assertEqual(radiodlg.port_label("/dev/ttyUSB0", "n/a"), "/dev/ttyUSB0")
        self.assertEqual(radiodlg.port_name("COM12"), "COM12")


if __name__ == "__main__":
    unittest.main()


class SansBlocage(unittest.TestCase):
    def test_derniere_erreur_tout_de_suite(self):
        """Poste qui ne répond pas : « Émettre » ne fige plus la fenêtre (dernière erreur donnée)."""
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        import threading
        import time

        class Stub:
            rig = None
            radio_cfg = {"rig": "hamlib:3073"}
            rig_lock = threading.RLock()
            _rig_err = (time.time(), RuntimeError("pas de réponse du poste"))

            def _rig_open(self):
                raise AssertionError("ne doit pas rouvrir la liaison")
        with self.assertRaises(RuntimeError) as cm:
            app.App._rig_open_now(Stub())
        self.assertIn("pas de réponse", str(cm.exception))


class KenwoodAI(unittest.TestCase):
    """1.61 : poste en « AI » (messages non demandés) et retour en LSB vérifié."""

    class Ser:
        def __init__(self, data):
            self.data, self.sent = data, []

        def reset_input_buffer(self):
            pass

        def write(self, b):
            self.sent.append(b)

        @property
        def in_waiting(self):
            return len(self.data)

        def read(self, n):
            b, self.data = self.data[:n], self.data[n:]
            return b

    def test_message_non_demande_ignore(self):
        s = self.Ser(b"RX0;FA00007058000;SF000007058000C;")
        self.assertEqual(audio._query(s, "SF0;"), "SF000007058000C;")

    def test_reponse_simple(self):
        self.assertEqual(audio._query(self.Ser(b"ID024;"), "ID;"), "ID024;")

    def test_refus(self):
        self.assertEqual(audio._query(self.Ser(b"?;"), "SF0;"), "?;")

    def test_retour_repete_si_ignore(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        logs = []

        class Rig(DataAuto.Rig):
            def set_voice(self, side):
                self.cmds.append(side)
                if self.cmds.count(side) >= 2:           # la 1re commande est ignorée par le poste
                    self.m = side

        class Stub:
            log = staticmethod(logs.append)
            ui = staticmethod(lambda fn, *a: fn(*a))

            class _rig_kick:
                set = staticmethod(lambda: None)
        r = Rig("LSB-DATA1")
        with mock.patch.object(app.time, "sleep", lambda s: None):
            app.App._data_auto_off(Stub(), r, "LSB")
        self.assertEqual((r.cmds, r.m), (["LSB", "LSB"], "LSB"))
        self.assertTrue(any("retour en LSB." in m for m in logs), logs)
