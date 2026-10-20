"""Présence des stations par Internet (comme la liste « En émission » d'EasyPal).

Chaque HFImage ouvert se signale sur un serveur MQTT public : indicatif, locator,
fréquence du poste, mode, état (réception / émission). Tous les programmes ouverts
voient donc immédiatement les autres, avec leur fréquence, sans rien émettre par radio.

- hfimage/v1/st/<INDICATIF>   : présence (message « retenu »), mise à jour chaque minute
                                 et à chaque changement de fréquence ; effacée à la
                                 fermeture (et par le « testament » MQTT en cas de plantage)
- hfimage/v1/rxok/<INDICATIF> : « j'ai bien reçu ton image » (report, locator) : remplit
                                 la liste Rx Ok de l'émetteur, même si l'ACK radio est perdu
- hfimage/v1/rxok/_           : « j'ai bien reçu l'image n° … » diffusé à tous : l'émetteur
                                 se reconnaît au numéro de l'image, et les autres stations
                                 qui ont reçu la même image voient aussi les reports
- hfimage/v1/hyb/<EMPREINTE>  : hybride éclair : lien de l'image dont l'empreinte (SHA-256
                                 abrégé) part par radio en DATAC0 ; publié juste avant chaque
                                 annonce radio (non retenu) et gardé 1 h par les stations

Aucune donnée personnelle autre que ce qui passe déjà sur l'air (indicatif, locator,
fréquence). Aucun mot de passe.
"""
import json
import random
import re
import threading
import time

BASE = "hfimage/v1"
DEFAULT_HOST = "broker.hivemq.com"
DEFAULT_PORT = 1883
STALE_S = 5 * 60          # une présence non rafraîchie depuis 5 min est considérée hors ligne
FLASH_KEEP_S = 3600       # hybride éclair : liens gardés 1 h
FLASH_MAX = 300           # et au plus 300 (les plus récents)
MAX_SIZE = (1 << 24) - 1      # hybride éclair : taille sur 3 octets (plus gros : annonce normale)


def _topic_call(call):
    return re.sub(r"[^A-Z0-9]", "-", (call or "").upper())[:16] or "NOCALL"


class Presence:
    """Client MQTT en tâche de fond. Les rappels sont appelés depuis le fil réseau :
    à l'appelant de les renvoyer dans le fil de l'interface."""

    def __init__(self, host, port, on_station, on_rxok, on_state, log=lambda m: None):
        self.host, self.port = host or DEFAULT_HOST, int(port or DEFAULT_PORT)
        self.on_station, self.on_rxok, self.on_state, self.log = on_station, on_rxok, on_state, log
        self.call, self.info = None, {}
        self.tag = ""             # profil (plusieurs HFImage ouverts) : une présence par instance
        self.client = None
        self.connected = False
        self.ever = False
        self._ports, self._try = [self.port], 0
        self._lock = threading.Lock()
        self.flash = {}           # empreinte -> (heure de réception, {call, url, size, crc, fmt, id})

    # ------------------------------------------------------------------ cycle de vie
    FALLBACK_PORTS = (8883, 8884, 8000)       # serveur par défaut : autres accès si 1883 est bloqué
    FALLBACK_S = 20                           # délai avant d'essayer l'accès suivant

    def start(self, call, info):
        self.call = (call or "").upper()
        self.info = dict(info)
        self.ever = False
        # serveur par défaut : si le port réglé est bloqué (pare-feu, fournisseur d'accès),
        # on essaie tout seul les autres accès du même serveur, jusqu'à ce que l'un réponde
        self._ports = [self.port]
        if self.host == DEFAULT_HOST:
            self._ports += [p for p in self.FALLBACK_PORTS if p != self.port]
        self._try = 0
        self._connect()

    def _connect(self):
        import paho.mqtt.client as mqtt
        self.port = self._ports[self._try % len(self._ports)]
        cid = f"hfimage-{_topic_call(self.call)}-{random.randrange(1 << 30):x}"
        # 1883 : MQTT simple ; 8883 : chiffré (TLS) ; 8000 / 8884 : par le web (websockets),
        # utile si un pare-feu bloque le port 1883
        ws = self.port in (8000, 8080, 8884, 443)
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid, clean_session=True,
                        transport="websockets" if ws else "tcp")
        if ws:
            c.ws_set_options(path="/mqtt")
        if self.port in (8883, 8884, 443):
            c.tls_set()
        c.will_set(self._st_topic(), b"", qos=1, retain=True)       # effacé si on disparaît
        c.on_connect = self._on_connect
        c.on_disconnect = self._on_disconnect
        c.on_message = self._on_message
        c.reconnect_delay_set(min_delay=2, max_delay=60)
        self.client = c
        c.connect_async(self.host, self.port, keepalive=60)
        c.loop_start()
        if len(self._ports) > 1:
            t = threading.Timer(self.FALLBACK_S, self._watchdog, args=(c,))
            t.daemon = True
            t.start()

    def _watchdog(self, c):
        """Pas de réponse sur ce port : on passe au suivant (tant qu'aucun n'a marché)."""
        if self.client is not c or self.connected or self.ever:
            return
        old = self.port
        self._try += 1
        try:
            c.loop_stop()
            c.disconnect()
        except Exception:
            pass
        self.client = None
        nxt = self._ports[self._try % len(self._ports)]
        self.log(f"Présence : pas de réponse du serveur sur le port {old}, essai du port {nxt}…")
        self._connect()

    def stop(self):
        c, self.client = self.client, None
        if c is None:
            return
        try:
            if self.connected:
                c.publish(self._st_topic(), b"", qos=1, retain=True).wait_for_publish(2)
            c.disconnect()
        except Exception:
            pass
        try:
            c.loop_stop()
        except Exception:
            pass
        self.connected = False

    def _st_key(self):
        tag = re.sub(r"[^A-Z0-9]", "", (self.tag or "").upper())[:8]
        return _topic_call(self.call) + (f"~{tag}" if tag else "")

    def _st_topic(self, call=None):
        return f"{BASE}/st/" + (_topic_call(call) if call else self._st_key())

    # ------------------------------------------------------------------ publication
    def update(self, **info):
        """Met à jour notre présence (fréquence, mode, état…) et la republie."""
        with self._lock:
            self.info.update(info)
            data = dict(self.info, call=self.call, t=int(time.time()))
        if self.client is not None and self.connected:
            self.client.publish(self._st_topic(), json.dumps(data).encode(), qos=1, retain=True)

    def send_rxok(self, to_call, image_id, report=None, loc=""):
        """Prévient l'émetteur que son image est bien arrivée chez nous."""
        if self.client is None or not self.connected:
            return False
        msg = {"from": self.call, "id": int(image_id), "report": report, "loc": loc, "t": int(time.time()),
               "freq": self.info.get("freq")}
        # diffusé à toutes les stations : l'émetteur remplit sa liste Rx Ok, et les autres
        # stations qui ont reçu la même image voient aussi les reports (comme EasyPal)
        msg["to"] = "" if not to_call or to_call == "?" else str(to_call).upper()
        self.client.publish(f"{BASE}/rxok/_", json.dumps(msg).encode(), qos=1)
        return True

    def publish_flash(self, key, call, url, size, crc, fmt, image_id):
        """Hybride éclair : publie le lien de l'image annoncée par radio sous son empreinte."""
        if self.client is None or not self.connected:
            return False
        msg = {"call": self.call or str(call).upper(), "url": url, "size": int(size), "crc": int(crc),
               "fmt": fmt, "id": int(image_id), "t": int(time.time())}
        self.client.publish(f"{BASE}/hyb/{key}", json.dumps(msg).encode(), qos=1)
        return True

    def get_flash(self, key):
        """Lien reçu pour cette empreinte -> dict, ou None."""
        with self._lock:
            e = self.flash.get(key)
        return dict(e[1]) if e and time.time() - e[0] < FLASH_KEEP_S else None

    def _store_flash(self, key, d):
        """Garde un lien d'hybride éclair après contrôle de chaque champ."""
        if not re.fullmatch(r"[0-9a-f]{12}", key or "") or not isinstance(d, dict):
            return
        url = d.get("url")
        if not isinstance(url, str) or len(url) > 1000 or not re.match(r"https?://", url, re.I):
            return
        try:
            rec = {"call": re.sub(r"[^A-Z0-9/-]", "", str(d.get("call") or "?").upper())[:16] or "?",
                   "url": url, "size": int(d["size"]), "crc": int(d["crc"]) & 0xFFFFFFFF,
                   "fmt": re.sub(r"[^a-z0-9]", "", str(d.get("fmt") or "bin").lower())[:8] or "bin",
                   "id": int(d.get("id", 0)) & 0xFFFF}
        except (KeyError, TypeError, ValueError):
            return
        if not 0 < rec["size"] <= MAX_SIZE:
            return
        now = time.time()
        with self._lock:
            self.flash[key] = (now, rec)
            if len(self.flash) > FLASH_MAX:
                for k, _ in sorted(self.flash.items(), key=lambda kv: kv[1][0])[:len(self.flash) - FLASH_MAX]:
                    del self.flash[k]

    # ------------------------------------------------------------------ rappels MQTT
    def _on_connect(self, client, userdata, flags, reason, props=None):
        if getattr(reason, "is_failure", False):
            self.connected = False
            self.on_state(False, str(reason))
            return
        self.connected = True
        if not self.ever and self._try:
            self.log(f"Présence : connecté par le port {self.port} (le port {self._ports[0]} semble bloqué).")
        self.ever = True
        client.subscribe(f"{BASE}/st/+", qos=1)
        client.subscribe(f"{BASE}/rxok/{_topic_call(self.call)}", qos=1)
        client.subscribe(f"{BASE}/rxok/_", qos=1)
        client.subscribe(f"{BASE}/hyb/+", qos=1)
        self.on_state(True, "")
        self.update()

    def _on_disconnect(self, client, userdata, flags, reason, props=None):
        was = self.connected
        self.connected = False
        if was:
            self.on_state(False, str(reason))

    def _on_message(self, client, userdata, msg):
        try:
            if msg.topic.startswith(f"{BASE}/st/"):
                call_t = msg.topic.rsplit("/", 1)[1]
                if call_t == self._st_key():
                    return
                if not msg.payload:
                    self.on_station(call_t, None)             # station partie
                    return
                d = json.loads(msg.payload.decode("utf-8"))
                if not isinstance(d, dict) or not d.get("call"):
                    return
                if time.time() - float(d.get("t", 0)) > STALE_S:
                    return                                     # présence ancienne (programme planté)
                self.on_station(call_t, d)                     # clé = indicatif du sujet
            elif msg.topic.startswith(f"{BASE}/hyb/"):
                if len(msg.payload) <= 2048:
                    self._store_flash(msg.topic.rsplit("/", 1)[1], json.loads(msg.payload.decode("utf-8")))
            elif msg.topic.startswith(f"{BASE}/rxok/"):
                d = json.loads(msg.payload.decode("utf-8"))
                if isinstance(d, dict) and d.get("from") and str(d["from"]).upper() != self.call:
                    self.on_rxok(d)
        except Exception as e:                                 # message mal formé : ignoré
            self.log(f"Présence : message ignoré ({e})")
