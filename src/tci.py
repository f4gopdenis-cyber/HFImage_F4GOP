"""Pilote TCI (Transceiver Control Interface, Expert Electronics) : SunSDR / ExpertSDR, et les
autres logiciels SDR qui parlent TCI.

TCI passe par une WebSocket (ws://hôte:40001 par défaut) : des commandes texte « NOM:args; »
dans les deux sens. ExpertSDR envoie d'abord son état (DEVICE, VFO, MODULATION, TRX…) puis
READY ; ensuite il prévient de chaque changement. On lit donc la fréquence et le mode sans les
demander sans cesse, et on commande :
  VFO:0,0,7058000;         fréquence du récepteur 0, voie A
  MODULATION:0,LSB;        mode (LSB, USB, DIGL, DIGU…)
  TRX:0,true; / TRX:0,false;   émission / réception
Le son passe, comme aujourd'hui, par les câbles audio virtuels (VAC) d'ExpertSDR.

Client WebSocket minimal (bibliothèque standard seulement) : trames texte, ping / pong, fermeture.
"""
import base64
import os
import socket
import struct
import threading
import time

DEFAULT_HOST = "127.0.0.1:40001"


class TciError(RuntimeError):
    pass


class TciClient:
    """Connexion TCI : envoi de commandes, état tenu à jour par un fil de lecture."""

    def __init__(self, host=DEFAULT_HOST, timeout=5.0, on_line=None):
        h, _, p = (host or DEFAULT_HOST).strip().rpartition(":")
        if not h:
            h, p = p, "40001"
        self.host, self.port = h or "127.0.0.1", int(p or 40001)
        self.state = {}                 # « vfo:0,0 » -> « 7058000 », « modulation:0 » -> « lsb »…
        self.device = ""
        self.ready = threading.Event()
        self.changed = threading.Condition()
        self.alive = True
        self.on_line = on_line
        self._wlock = threading.Lock()
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        except OSError as e:
            raise TciError(f"TCI : pas de réponse de {self.host}:{self.port} ({e}). ExpertSDR est-il "
                           "lancé, avec TCI activé (Options → TCI) ?") from e
        self.sock.settimeout(timeout)
        self._handshake()
        self.sock.settimeout(None)
        self._buf = b""
        threading.Thread(target=self._reader, daemon=True).start()
        if not self.ready.wait(timeout):
            # certains serveurs n'envoient pas READY : on continue si l'état est arrivé
            if not self.state:
                self.close()
                raise TciError("TCI : le serveur n'a pas envoyé son état (READY)")

    # ------------------------------------------------------------------ WebSocket
    def _handshake(self):
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET / HTTP/1.1\r\nHost: {self.host}:{self.port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            b = self.sock.recv(1024)
            if not b:
                raise TciError("TCI : connexion refusée par le serveur")
            resp += b
            if len(resp) > 16384:
                raise TciError("TCI : réponse inattendue du serveur")
        head, _, rest = resp.partition(b"\r\n\r\n")
        if b" 101" not in head.split(b"\r\n", 1)[0]:
            raise TciError("TCI : le serveur n'a pas accepté la connexion WebSocket")
        self._pending = rest

    def _send_frame(self, opcode, payload=b""):
        mask = os.urandom(4)
        n = len(payload)
        hdr = bytes([0x80 | opcode])
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        with self._wlock:
            self.sock.sendall(hdr + mask + body)

    def _recv_exact(self, n):
        while len(self._buf) < n:
            if self._pending:
                self._buf += self._pending
                self._pending = b""
                continue
            b = self.sock.recv(65536)
            if not b:
                raise ConnectionError("connexion fermée")
            self._buf += b
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _read_frame(self):
        b0, b1 = self._recv_exact(2)
        opcode, n = b0 & 0x0F, b1 & 0x7F
        if n == 126:
            n = struct.unpack(">H", self._recv_exact(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if b1 & 0x80 else None
        data = self._recv_exact(n)
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        return opcode, data

    def _reader(self):
        try:
            while self.alive:
                op, data = self._read_frame()
                if op == 0x1:                                   # texte : commandes
                    for line in data.decode("utf-8", "replace").split(";"):
                        if line.strip():
                            self._handle(line.strip())
                elif op == 0x9:                                 # ping -> pong
                    self._send_frame(0xA, data)
                elif op == 0x8:                                 # fermeture
                    break
                # 0x2 (audio / IQ) : non demandé, ignoré
        except Exception:
            pass
        self.alive = False
        with self.changed:
            self.changed.notify_all()

    def _handle(self, line):
        name, _, args = line.partition(":")
        name = name.strip().lower()
        parts = [a.strip() for a in args.split(",")] if args else []
        if self.on_line:
            self.on_line(line)
        if name == "ready":
            self.ready.set()
        elif name == "device" and parts:
            self.device = parts[0]
        elif name == "vfo" and len(parts) >= 3:
            self.state[f"vfo:{parts[0]},{parts[1]}"] = parts[2]
        elif name in ("modulation", "trx", "dds") and len(parts) >= 2:
            self.state[f"{name}:{parts[0]}"] = parts[1]
        with self.changed:
            self.changed.notify_all()

    # ------------------------------------------------------------------ commandes
    def send(self, cmd):
        if not self.alive:
            raise TciError("TCI : connexion perdue")
        if not cmd.endswith(";"):
            cmd += ";"
        self._send_frame(0x1, cmd.encode())

    def query(self, key, cmd, timeout=1.5):
        """Valeur de l'état (ex. « vfo:0,0 ») ; la demande au serveur si elle n'est pas encore connue."""
        if key in self.state:
            return self.state[key]
        self.send(cmd)
        end = time.time() + timeout
        with self.changed:
            while key not in self.state and self.alive and time.time() < end:
                self.changed.wait(0.1)
        return self.state.get(key)

    def wait_for(self, key, value, timeout=1.5):
        end = time.time() + timeout
        with self.changed:
            while str(self.state.get(key, "")).lower() != str(value).lower() and time.time() < end:
                if not self.alive:
                    break
                self.changed.wait(0.1)
        return str(self.state.get(key, "")).lower() == str(value).lower()

    def close(self):
        self.alive = False
        try:
            self._send_frame(0x8, b"")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
