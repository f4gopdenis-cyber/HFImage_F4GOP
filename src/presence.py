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


def _topic_call(call):
    return re.sub(r"[^A-Z0-9]", "-", (call or "").upper())[:16] or "NOCALL"


class Presence:
    """Client MQTT en tâche de fond. Les rappels sont appelés depuis le fil réseau :
    à l'appelant de les renvoyer dans le fil de l'interface."""

    def __init__(self, host, port, on_station, on_rxok, on_state, log=lambda m: None):
        self.host, self.port = host or DEFAULT_HOST, int(port or DEFAULT_PORT)
        self.on_station, self.on_rxok, self.on_state, self.log = on_station, on_rxok, on_state, log
        self.call, self.info = None, {}
        self.client = None
        self.connected = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ cycle de vie
    def start(self, call, info):
        import paho.mqtt.client as mqtt
        self.call = (call or "").upper()
        self.info = dict(info)
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

    def _st_topic(self, call=None):
        return f"{BASE}/st/{_topic_call(call or self.call)}"

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

    # ------------------------------------------------------------------ rappels MQTT
    def _on_connect(self, client, userdata, flags, reason, props=None):
        if getattr(reason, "is_failure", False):
            self.connected = False
            self.on_state(False, str(reason))
            return
        self.connected = True
        client.subscribe(f"{BASE}/st/+", qos=1)
        client.subscribe(f"{BASE}/rxok/{_topic_call(self.call)}", qos=1)
        client.subscribe(f"{BASE}/rxok/_", qos=1)
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
                if call_t == _topic_call(self.call):
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
            elif msg.topic.startswith(f"{BASE}/rxok/"):
                d = json.loads(msg.payload.decode("utf-8"))
                if isinstance(d, dict) and d.get("from") and str(d["from"]).upper() != self.call:
                    self.on_rxok(d)
        except Exception as e:                                 # message mal formé : ignoré
            self.log(f"Présence : message ignoré ({e})")
