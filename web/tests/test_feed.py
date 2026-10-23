import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ucm_web import mqtt_source  # noqa: E402
from ucm_web.app import create_app  # noqa: E402
from ucm_web.config import Config  # noqa: E402
from ucm_web.store import LatestStore  # noqa: E402


ENV = b'{"node":"UCM-E0A695","pm25":3.0}'


class FakeMessage:

    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload


# ---------------- STORE ----------------

def test_keeps_only_latest_per_node_and_kind():

    store = LatestStore()
    store.record("ucm/node-UCM-E0A695/environment", b'{"pm25":1}')
    store.record("ucm/node-UCM-E0A695/environment", b'{"pm25":2}')
    store.record("ucm/node-UCM-E0A695/heartbeat", b'{}')

    nodes = json.loads(store.body("test")[1])["nodes"]

    assert list(nodes) == ["UCM-E0A695"]
    assert nodes["UCM-E0A695"]["environment"]["payload"] == '{"pm25":2}'
    assert set(nodes["UCM-E0A695"]) == {"environment", "heartbeat"}


def test_drops_bad_topics():

    store = LatestStore()

    for topic in ["ucm/node-X/unknown", "other/node-X/environment", "ucm/X/environment",
                  "ucm/node-/environment", "ucm/node-a/b/environment",
                  "ucm/node-" + "x" * 100 + "/environment", "ucm/node-<script>/info"]:
        assert store.record(topic, ENV) == "dropped_bad_topic", topic

    assert store.stats()["nodes"] == 0


def test_drops_oversized_payload():

    store = LatestStore(max_payload_bytes=100)
    assert store.record("ucm/node-A/environment", b"x" * 101) == "dropped_too_large"
    assert store.record("ucm/node-A/environment", b"x" * 100) == "accepted"


def test_caps_number_of_nodes():

    store = LatestStore(max_nodes=3)

    for i in range(10):
        store.record(f"ucm/node-N{i}/environment", ENV)

    stats = store.stats()
    assert stats["nodes"] == 3
    assert stats["dropped_too_many_nodes"] == 7

    # Known nodes keep updating after the cap is reached.
    assert store.record("ucm/node-N0/environment", ENV) == "accepted"


def test_invalid_utf8_does_not_crash():

    store = LatestStore()
    assert store.record("ucm/node-A/environment", b"\xff\xfe{bad") == "accepted"
    json.loads(store.body("test")[1])


def test_concurrent_writers_and_readers():

    store = LatestStore()
    errors = []

    def write(n):
        try:
            for i in range(2000):
                store.record(f"ucm/node-W{n}/environment", b'{"i":%d}' % i)
        except Exception as exc:
            errors.append(exc)

    def read():
        try:
            for _ in range(500):
                json.loads(store.body("test")[1])
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(n,)) for n in range(15)]
    threads += [threading.Thread(target=read) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert store.stats()["accepted"] == 15 * 2000
    assert store.version == 15 * 2000


# ---------------- MQTT CALLBACKS ----------------

def test_mqtt_on_message_never_raises():

    store = LatestStore()
    client = mqtt_source.build_client(Config(), store)

    client.on_message(client, None, FakeMessage("ucm/node-A/environment", ENV))
    client.on_message(client, None, FakeMessage(None, None))
    client.on_message(client, None, FakeMessage("ucm/node-B/environment", None))
    client.on_message(client, None, object())

    assert store.stats()["nodes"] == 1


# ---------------- WEB APP ----------------

def test_api_returns_304_when_unchanged():

    store = LatestStore()
    store.record("ucm/node-A/environment", ENV)
    client = create_app(store, "test").test_client()

    first = client.get("/api/raw")
    assert first.status_code == 200
    assert json.loads(first.data)["nodes"]["A"]["environment"]["payload"] == ENV.decode()

    etag = first.headers["ETag"]
    assert client.get("/api/raw", headers={"If-None-Match": etag}).status_code == 304

    store.record("ucm/node-A/environment", b'{"pm25":9}')
    assert client.get("/api/raw", headers={"If-None-Match": etag}).status_code == 200


def test_healthz_and_index():

    store = LatestStore()
    client = create_app(store, "test").test_client()

    assert client.get("/healthz").json["nodes"] == 0
    assert b"UCM raw sensor feed" in client.get("/").data
