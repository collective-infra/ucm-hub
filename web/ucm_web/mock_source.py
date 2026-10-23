import json
import logging
import random
import threading
import time
from datetime import datetime, timezone


# ---------------- MOCK SOURCE ----------------
#
# Generates payloads shaped like the real firmware's (see the
# UCM-collector-server README), at a configurable rate, so the site can be
# developed and load-tested without a broker.

log = logging.getLogger(__name__)


def mock_node_ids(count):
    return [f"UCM-MOCK{i:02d}" for i in range(1, count + 1)]


def publish_once(store, node_ids, started):

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for node_id in node_ids:
        pm25 = round(random.uniform(2, 15), 1)

        store.record(f"ucm/node-{node_id}/environment", json.dumps({
            "node": node_id,
            "timestamp": timestamp,
            "pm1": round(pm25 * 0.9, 1),
            "pm25": pm25,
            "pm4": round(pm25 * 1.05, 1),
            "pm10": round(pm25 * 1.1, 1),
            "temperature": round(random.uniform(18, 24), 1),
            "humidity": round(random.uniform(40, 60), 1),
            "voc": round(random.uniform(90, 120), 1),
        }).encode())

        store.record(f"ucm/node-{node_id}/heartbeat", json.dumps({
            "node": node_id,
            "timestamp": timestamp,
            "uptime_s": int(time.time() - started),
            "free_heap": random.randint(180000, 200000),
            "rssi": random.randint(-75, -50),
        }).encode())


def start(config, store):

    node_ids = mock_node_ids(config.mock_nodes)
    interval = 1.0 / config.mock_hz

    for i, node_id in enumerate(node_ids):
        store.record(f"ucm/node-{node_id}/status",
                     json.dumps({"node": node_id, "status": "online"}).encode())
        store.record(f"ucm/node-{node_id}/info",
                     json.dumps({"node": node_id, "name": f"mock node {i + 1}",
                                 "description": "mock", "lat": 40.7, "lon": -73.95}).encode())

    store.set_status(
        f"mock mode: {len(node_ids)} nodes at {config.mock_hz:g} msg/s each"
    )

    def run():
        started = time.time()
        next_tick = started
        while True:
            try:
                publish_once(store, node_ids, started)
            except Exception:
                log.exception("mock tick failed")
            next_tick += interval
            time.sleep(max(0.0, next_tick - time.time()))

    thread = threading.Thread(target=run, name="mock-source", daemon=True)
    thread.start()
    return thread
