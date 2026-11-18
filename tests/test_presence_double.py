"""2.44 : présence sur deux serveurs publics à la fois (HiveMQ + EMQX), listes fusionnées ; la liste
des stations n'est plus vidée à la moindre coupure ; raison d'un refus écrite en clair."""
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import presence  # noqa: E402


def make(**kw):
    got = {"st": [], "rx": [], "state": [], "log": []}
    mp = presence.MultiPresence(kw.get("host", presence.DEFAULT_HOST), 1883,
                                on_station=lambda k, d: got["st"].append((k, d)),
                                on_rxok=lambda d: got["rx"].append(d),
                                on_state=lambda ok, why: got["state"].append(ok),
                                log=got["log"].append)
    return mp, got


class Fusion(unittest.TestCase):
    def test_deux_serveurs_par_defaut(self):
        mp, _ = make()
        self.assertEqual([m.host for m in mp.members], [presence.DEFAULT_HOST, presence.SECOND_HOST])
        mp2, _ = make(host="mqtt.monclub.fr")
        self.assertEqual([m.host for m in mp2.members], ["mqtt.monclub.fr"])     # serveur perso : seul

    def test_station_vue_par_deux_serveurs(self):
        mp, got = make()
        a, b = mp.members
        d = {"call": "VK6NJP", "freq": 14233000}
        a.on_station("VK6NJP", d)
        b.on_station("VK6NJP", d)
        a.on_station("VK6NJP", None)                          # partie de HiveMQ seulement
        self.assertEqual(got["st"][-1], ("VK6NJP", d))        # toujours là (vue par EMQX)
        b.on_station("VK6NJP", None)
        self.assertEqual(got["st"][-1], ("VK6NJP", None))     # partie des deux : partie

    def test_rxok_une_seule_fois(self):
        mp, got = make()
        a, b = mp.members
        r = {"from": "G4PEN", "id": 1234, "to": "F4GOP", "report": 7}
        a.on_rxok(dict(r))
        b.on_rxok(dict(r))
        self.assertEqual(len(got["rx"]), 1)
        a.on_rxok(dict(r, id=99))
        self.assertEqual(len(got["rx"]), 2)

    def test_etat_un_serveur_suffit(self):
        mp, got = make()
        a, b = mp.members
        a.connected = True
        a.on_state(True, "")
        self.assertTrue(mp.connected)
        self.assertEqual(got["state"][-1], True)
        b.on_state(False, "Connection rate exceeded")         # EMQX refuse : HiveMQ suffit
        self.assertTrue(got["state"][-1])
        a.connected = False
        a.on_state(False, "")
        self.assertEqual(got["state"][-1], False)

    def test_publication_sur_les_deux(self):
        mp, _ = make()
        for m in mp.members:
            m.client, m.connected, m.call = mock.MagicMock(), True, "F4GOP"
        self.assertTrue(mp.send_rxok("G4PEN", 12, 5, "IN98QR"))
        self.assertTrue(all(m.client.publish.called for m in mp.members))
        mp.members[1].flash["abcdef012345"] = (time.time(), {"url": "https://x/y.jpg"})
        self.assertEqual(mp.get_flash("abcdef012345")["url"], "https://x/y.jpg")
        mp.tag = "20M"
        self.assertEqual([m.tag for m in mp.members], ["20M", "20M"])

    def test_raison_en_clair(self):
        p = presence.Presence(presence.DEFAULT_HOST, 1883, None, None, None)
        self.assertIn("surchargé", p._why("Connection rate exceeded"))
        self.assertIn("refusée", p._why("Not authorized"))
        logs = []
        p.log = logs.append
        p.on_state = lambda *a: None
        class Refus:
            is_failure = True

            def __str__(self):
                return "Connection rate exceeded"
        p._on_connect(None, None, None, Refus())
        p._on_connect(None, None, None, Refus())
        self.assertEqual(len(logs), 1)                        # pas répété à chaque essai
        self.assertIn("broker.hivemq.com", logs[0])
        self.assertIn("surchargé", logs[0])

    def test_ports_de_secours_emqx(self):
        p = presence.Presence(presence.SECOND_HOST, 1883, None, None, None)
        with mock.patch.object(p, "_connect"):
            p.start("F4GOP", {})
        self.assertEqual(p._ports, [1883, 8883, 8084, 8083])


class ListeGardee(unittest.TestCase):
    def test_coupure_ne_vide_pas_la_liste(self):
        import gc
        import json
        import tempfile
        try:
            import app
        except (ImportError, OSError) as e:
            raise unittest.SkipTest(str(e))
        conf = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(conf, "w") as f:
            json.dump({"callsign": "F4GOP", "licence_ok": "1.0", "lang": "fr", "net_on": False}, f)
        gc.collect()
        with mock.patch.object(app, "CONF_PATH", conf):
            try:
                a = app.App()
            except Exception as e:
                raise unittest.SkipTest(str(e))
            try:
                a.online["G4PEN"] = {"call": "G4PEN", "seen": time.time(), "t": time.time(), "state": "RX"}
                a.net_ok = True
                a._net_state(False, "coupure")
                self.assertIn("G4PEN", a.online)               # gardée pendant la coupure
                a.online["G4PEN"]["seen"] = a.online["G4PEN"]["t"] = time.time() - 6 * 60
                a._heard_refresh()
                self.assertNotIn("G4PEN", a.online)            # sans nouvelles depuis 6 min : partie
            finally:
                a.destroy()


if __name__ == "__main__":
    unittest.main()
