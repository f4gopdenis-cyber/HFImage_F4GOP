"""Version 1.65 : partage du poste (Hamlib NET rigctl) ; état « en émission » des autres stations."""
import json
import os
import socket
import sys
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import presence  # noqa: E402
import radio  # noqa: E402


def cfg(**kw):
    c = dict(radio.DEFAULTS)
    c.update(kw)
    return c


class Partage(unittest.TestCase):
    def test_postes_partageables(self):
        self.assertTrue(radio.can_share(cfg(rig="hamlib:1035")))           # FT-991 / FT-991A
        self.assertTrue(radio.can_share(cfg(rig="hamlib:2039")))           # TS-990S (Kenwood en direct)
        self.assertFalse(radio.can_share(cfg(rig="kenwood")))              # modèle inconnu
        for k in ("none", "custom", "tci", "flrig", "netrigctl"):
            self.assertFalse(radio.can_share(cfg(rig=k)), k)

    def test_kenwood_passe_par_hamlib_quand_on_partage(self):
        self.assertEqual(radio.effective(cfg(rig="hamlib:2039"))["kind"], "kenwood")
        self.assertEqual(radio.effective(cfg(rig="hamlib:2039", share=True))["kind"], "hamlib")

    def test_partage_rouvre_la_liaison(self):
        self.assertNotEqual(radio.cat_signature(cfg(rig="hamlib:1035")),
                            radio.cat_signature(cfg(rig="hamlib:1035", share=True)))

    def run_rigctld(self, c, busy=False):
        runs = []

        class Proc:
            def __init__(self, args, **kw):
                runs.append(args)
                self.pid, self.returncode = 1, None

            def poll(self):
                return None

            def kill(self):
                self.returncode = -9

            terminate = kill

            def wait(self, timeout=None):
                return 0

        def fake_init(self, cfg, host, port, label):
            self.sock = None
        with mock.patch.object(radio, "find_rigctld", lambda: "/usr/bin/rigctld"), \
                mock.patch.object(radio.subprocess, "Popen", Proc), \
                mock.patch.object(radio.RigctlRig, "__init__", fake_init), \
                mock.patch.object(radio.RigctlRig, "freq", lambda self: 7058000), \
                mock.patch.object(radio, "_kill_with_us", lambda p: None), \
                mock.patch.object(radio, "_port_free", lambda p: not busy), \
                mock.patch("builtins.open", mock.mock_open()):
            r = radio.make_rig(c)
        return r, runs

    def test_port_fixe_4532_en_local(self):
        r, runs = self.run_rigctld(cfg(rig="hamlib:2039", port="COM5", share=True))
        a = runs[-1]
        self.assertEqual(r.kind, "hamlib")
        self.assertEqual(a[a.index("-t") + 1], "4532")
        self.assertEqual(a[a.index("-T") + 1], "127.0.0.1")                # pas ouvert au réseau
        self.assertEqual(a[a.index("-m") + 1], "2039")

    def test_autre_port(self):
        _, runs = self.run_rigctld(cfg(rig="hamlib:1035", port="COM5", share=True, share_port=4533))
        self.assertEqual(runs[-1][runs[-1].index("-t") + 1], "4533")

    def test_sans_partage_port_au_hasard(self):
        _, runs = self.run_rigctld(cfg(rig="hamlib:1035", port="COM5"))
        self.assertNotEqual(runs[-1][runs[-1].index("-t") + 1], "4532")

    def test_port_deja_pris(self):
        with self.assertRaises(RuntimeError) as cm:
            self.run_rigctld(cfg(rig="hamlib:1035", port="COM5", share=True), busy=True)
        self.assertIn("4532", str(cm.exception))

    def test_ptt_rts_kenwood_partage(self):
        # Kenwood partagé : rigctld tient le port, le PTT RTS passe par lui
        class R(radio.RigBase):
            kind, port = "hamlib", "COM5"
        p = radio.Ptt(cfg(rig="hamlib:2039", port="COM5", ptt="RTS", share=True), R())
        self.assertEqual(p.method, "CAT")

    def test_port_libre(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        try:
            self.assertFalse(radio._port_free(s.getsockname()[1]))
        finally:
            s.close()


class EnEmission(unittest.TestCase):
    def app(self):
        try:
            import app
        except ImportError as e:
            self.skipTest(str(e))
        return app.App

    def test_etoile_seulement_si_recent(self):
        self.app()
        import app
        A = app
        now = time.time()
        self.assertTrue(A.on_air({"state": "TX", "seen": now - 30}, now))
        self.assertFalse(A.on_air({"state": "TX", "seen": now - 200}, now))      # état oublié
        self.assertFalse(A.on_air({"state": "RX", "seen": now}, now))
        # horloge de l'autre PC en avance d'une heure : seule l'heure de réception compte
        self.assertFalse(A.on_air({"state": "TX", "seen": now - 200, "t": now + 3600}, now))

    def message(self, d, retain):
        got = []
        p = presence.Presence.__new__(presence.Presence)
        p.call, p.tag = "F4GOP", ""
        p.on_station = lambda k, v: got.append((k, v))
        p.log = lambda m: None
        msg = types.SimpleNamespace(topic=f"{presence.BASE}/st/F1ABC", payload=json.dumps(d).encode(),
                                    retain=retain)
        p._on_message(None, None, msg)
        return got

    def test_horloge_en_retard_prise_en_direct(self):
        d = {"call": "F1ABC", "state": "RX", "t": int(time.time()) - 3600}       # PC en retard d'1 h
        self.assertEqual(len(self.message(d, retain=False)), 1)

    def test_presence_gardee_ancienne_ignoree(self):
        d = {"call": "F1ABC", "state": "TX", "t": int(time.time()) - 3600}
        self.assertEqual(self.message(d, retain=True), [])


if __name__ == "__main__":
    unittest.main()
