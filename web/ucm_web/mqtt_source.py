import logging

import paho.mqtt.client as mqtt


# ---------------- MQTT SOURCE ----------------
#
# Subscribes to the node topics and hands every message to the store.
# paho runs these callbacks on its network thread; an exception escaping a
# callback stops that thread and the feed goes silent, so each callback
# catches and logs everything.

log = logging.getLogger(__name__)

TOPICS = [
    ("ucm/+/environment", 0),
    ("ucm/+/info", 0),
    ("ucm/+/status", 0),
]


def build_client(config, store):
    """Create a configured client without connecting (tests use this)."""

    target = f"{config.mqtt_host}:{config.mqtt_port}"

    def on_connect(client, userdata, flags, reason_code, properties):
        try:
            if reason_code.is_failure:
                store.set_status(f"MQTT connect refused by {target}: {reason_code}")
                return
            client.subscribe(TOPICS)
            store.set_status(f"connected to {target}")
            log.info("connected to %s", target)
        except Exception:
            log.exception("on_connect failed")

    def on_connect_fail(client, userdata):
        try:
            store.set_status(f"cannot reach {target} (are you on the mesh?), retrying")
        except Exception:
            log.exception("on_connect_fail failed")

    def on_disconnect(client, userdata, flags, reason_code, properties):
        try:
            store.set_status(f"disconnected from {target} ({reason_code}), retrying")
            log.warning("disconnected: %s", reason_code)
        except Exception:
            log.exception("on_disconnect failed")

    def on_message(client, userdata, msg):
        try:
            store.record(msg.topic, msg.payload)
        except Exception:
            log.exception("dropped message on %r", getattr(msg, "topic", "?"))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if config.mqtt_user:
        client.username_pw_set(config.mqtt_user, config.mqtt_password)

    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.suppress_exceptions = True
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    return client


def start(config, store):

    client = build_client(config, store)

    store.set_status(f"connecting to {config.mqtt_host}:{config.mqtt_port}")

    # connect_async + loop_start: the loop thread keeps retrying in the
    # background, so a down broker never takes the web page down with it.
    client.connect_async(config.mqtt_host, config.mqtt_port, keepalive=30)
    client.loop_start()

    return client
