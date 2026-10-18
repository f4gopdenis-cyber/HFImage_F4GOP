"""Version 0.76 : ports COM vus par le registre Windows, accès de secours au serveur des stations."""
import os
import sys
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import audio  # noqa: E402
import serial.tools.list_ports  # noqa: E402,F401
import presence  # noqa: E402


class FakeWinreg(types.ModuleType):
    """Registre de RK1AT : COM1/2 (carte PCI), COM4 (Prolific), COM3/7/9 (USB)."""
    HKEY_LOCAL_MACHINE = 1
    VALUES = [(r"\Device\Serial0", "COM1"), (r"\Device\Serial1", "COM2"), (r"\Device\ProlificSerial0", "COM4"),
              (r"\Device\Silabser0", "COM3"), (r"\Device\VCP0", "COM7"), (r"\Device\Silabser1", "COM9")]

    def __init__(self):
        super().__init__("winreg")

    def OpenKey(self, root, path):
        assert path == r"HARDWARE\DEVICEMAP\SERIALCOMM"
        return mock.MagicMock(__enter__=lambda s: s, __exit__=lambda *a: False)

    def EnumValue(self, k, i):
        if i >= len(self.VALUES):
            raise OSError
        n, v = self.VALUES[i]
        return n, v, 1


class Ports(unittest.TestCase):
    def test_ports_du_registre_ajoutes(self):
        seen = [types.SimpleNamespace(device=d, description=t) for d, t in
                (("COM7", "USB Serial Port (COM7)"), ("COM1", "Port série (COM1)"), ("COM2", "Port série (COM2)"))]
        with mock.patch.dict(sys.modules, {"winreg": FakeWinreg()}), mock.patch.object(audio.sys, "platform", "win32"), \
                mock.patch("serial.tools.list_ports.comports", lambda: seen):
            got = audio.ports_list()
        self.assertEqual([p for p, _ in got], ["COM1", "COM2", "COM3", "COM4", "COM7", "COM9"])
        self.assertEqual(dict(got)["COM7"], "USB Serial Port (COM7)")      # description pyserial gardée
        self.assertEqual(dict(got)["COM4"], "ProlificSerial0")

    def test_hors_windows(self):
        with mock.patch.object(audio.sys, "platform", "linux"):
            self.assertEqual(audio._registry_ports(), [])


class FakeClient:
    """Client MQTT simulé : seul le port 8884 répond."""
    made = []

    def __init__(self, *a, **k):
        self.port = None
        FakeClient.made.append(self)

    def ws_set_options(self, **k):
        pass

    def tls_set(self):
        pass

    def will_set(self, *a, **k):
        pass

    def reconnect_delay_set(self, **k):
        pass

    def connect_async(self, host, port, keepalive=60):
        self.port = port

    def loop_start(self):
        if self.port == 8884:
            self.on_connect(self, None, None, types.SimpleNamespace(is_failure=False))

    def loop_stop(self):
        pass

    def disconnect(self):
        pass

    def subscribe(self, *a, **k):
        pass

    def publish(self, *a, **k):
        return mock.MagicMock()


class Secours(unittest.TestCase):
    def test_port_1883_bloque(self):
        import paho.mqtt.client as mqtt
        FakeClient.made.clear()
        logs, states = [], []
        p = presence.Presence(presence.DEFAULT_HOST, 1883, lambda *a: None, lambda *a: None,
                              lambda ok, why: states.append(ok), log=logs.append)
        with mock.patch.object(mqtt, "Client", FakeClient), mock.patch.object(presence.Presence, "FALLBACK_S", 0.05):
            p.start("RK1AT", {"loc": "KP50EA"})
            for _ in range(100):
                if p.connected:
                    break
                time.sleep(0.02)
        self.assertTrue(p.connected)
        self.assertEqual([c.port for c in FakeClient.made], [1883, 8883, 8884])
        self.assertIn(True, states)
        self.assertTrue(any("8884" in m for m in logs))

    def test_serveur_perso_sans_secours(self):
        p = presence.Presence("mqtt.monclub.fr", 1883, None, None, None)
        p.call, p.info = "F4GOP", {}
        p._ports = [1883]
        self.assertEqual(presence.Presence.FALLBACK_PORTS, (8883, 8884, 8000))


if __name__ == "__main__":
    unittest.main()
