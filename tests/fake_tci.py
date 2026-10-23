"""Faux serveur TCI (ExpertSDR) pour les essais : WebSocket minimale, répond comme ExpertSDR."""
import base64
import hashlib
import socket
import struct
import threading


class FakeTci:
    def __init__(self, device="SunSDR2PRO", freq=7058000, mode="lsb", send_ready=True):
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(5)
        self.port = self.srv.getsockname()[1]
        self.got = []
        self.state = {"vfo": freq, "mode": mode, "trx": "false"}
        self.device, self.send_ready = device, send_ready
        self.conns = []
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            self.conns.append(c)
            threading.Thread(target=self._serve, args=(c,), daemon=True).start()

    @staticmethod
    def _frame(text):
        p = text.encode()
        n = len(p)
        hdr = bytes([0x81]) + (bytes([n]) if n < 126 else bytes([126]) + struct.pack(">H", n))
        return hdr + p

    def push(self, text):
        for c in list(self.conns):
            try:
                c.sendall(self._frame(text))
            except OSError:
                pass

    def _serve(self, c):
        req = b""
        while b"\r\n\r\n" not in req:
            req += c.recv(1024)
        key = [l.split(b":", 1)[1].strip() for l in req.split(b"\r\n") if l.lower().startswith(b"sec-websocket-key")][0]
        acc = base64.b64encode(hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()).decode()
        c.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Accept: {acc}\r\n\r\n").encode())
        init = (f"protocol:ExpertSDR3,2.1;device:{self.device};trx_count:2;vfo:0,0,{self.state['vfo']};"
                f"modulation:0,{self.state['mode']};trx:0,{self.state['trx']};" + ("ready;" if self.send_ready else ""))
        c.sendall(self._frame(init))
        buf = b""
        try:
            while True:
                while len(buf) < 2:
                    d = c.recv(4096)
                    if not d:
                        return
                    buf += d
                op, n = buf[0] & 0x0F, buf[1] & 0x7F
                i = 2
                if n == 126:
                    n = struct.unpack(">H", buf[2:4])[0]
                    i = 4
                while len(buf) < i + 4 + n:
                    buf += c.recv(4096)
                mask, data = buf[i:i + 4], buf[i + 4:i + 4 + n]
                buf = buf[i + 4 + n:]
                text = bytes(b ^ mask[k % 4] for k, b in enumerate(data)).decode()
                if op == 8:
                    return
                for cmd in [x for x in text.split(";") if x]:
                    self.got.append(cmd)
                    name, _, args = cmd.partition(":")
                    a = args.split(",")
                    name = name.lower()
                    if name == "vfo" and len(a) == 3:
                        self.state["vfo"] = int(a[2])
                        c.sendall(self._frame(f"vfo:0,0,{self.state['vfo']};"))
                    elif name == "vfo":
                        c.sendall(self._frame(f"vfo:0,0,{self.state['vfo']};"))
                    elif name == "modulation" and len(a) == 2:
                        self.state["mode"] = a[1].lower()
                        c.sendall(self._frame(f"modulation:0,{self.state['mode']};"))
                    elif name == "trx" and len(a) >= 2:
                        self.state["trx"] = a[1]
                        c.sendall(self._frame(f"trx:0,{a[1]};"))
        except OSError:
            return

    def close(self):
        for c in self.conns:
            try:
                c.close()
            except OSError:
                pass
        self.srv.close()
