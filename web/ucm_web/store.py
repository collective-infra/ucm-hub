import json
import re
import threading
from datetime import datetime, timezone


# ---------------- LATEST-VALUE STORE ----------------
#
# Holds only the newest payload per node and topic kind, so memory stays
# flat however long the server runs and however fast nodes publish.
# Everything here is thread-safe: MQTT callbacks write while web threads read.

# Heartbeats are not kept: they only said when a node was last active,
# which the time of its latest environment reading already shows, and the
# current firmware no longer sends them.
KINDS = ("environment", "info", "status")

NODE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class LatestStore:

    def __init__(self, max_nodes=200, max_payload_bytes=4096):

        self.max_nodes = max_nodes
        self.max_payload_bytes = max_payload_bytes

        self._lock = threading.Lock()
        self._nodes = {}
        self._status = "starting"
        self._version = 0

        self._stats = {
            "received": 0,
            "accepted": 0,
            "dropped_bad_topic": 0,
            "dropped_too_large": 0,
            "dropped_too_many_nodes": 0,
        }

        # The JSON body is built once per version and shared by every
        # viewer, instead of being re-serialized on each request.
        self._cached_version = -1
        self._cached_body = b""

    # ---------------- WRITES ----------------

    def record(self, topic, payload):
        """Store one MQTT message. Returns "accepted" or the drop reason."""

        with self._lock:
            self._stats["received"] += 1

        parts = topic.split("/") if isinstance(topic, str) else []

        if (len(parts) != 3 or parts[0] != "ucm"
                or not parts[1].startswith("node-") or parts[2] not in KINDS):
            return self._drop("dropped_bad_topic")

        node_id = parts[1][len("node-"):]

        if not NODE_ID_PATTERN.match(node_id):
            return self._drop("dropped_bad_topic")

        if len(payload) > self.max_payload_bytes:
            return self._drop("dropped_too_large")

        if isinstance(payload, bytes):
            text = payload.decode("utf-8", errors="replace")
        else:
            text = str(payload)

        entry = {"payload": text, "received_at": now_iso()}

        with self._lock:

            if node_id not in self._nodes and len(self._nodes) >= self.max_nodes:
                self._stats["dropped_too_many_nodes"] += 1
                return "dropped_too_many_nodes"

            # Entries are replaced, never mutated, so a snapshot can
            # safely share them.
            self._nodes.setdefault(node_id, {})[parts[2]] = entry
            self._stats["accepted"] += 1
            self._version += 1

        return "accepted"

    def set_status(self, text):

        with self._lock:
            if text != self._status:
                self._status = text
                self._version += 1

    def _drop(self, reason):

        with self._lock:
            self._stats[reason] += 1

        return reason

    # ---------------- READS ----------------

    @property
    def version(self):

        with self._lock:
            return self._version

    def stats(self):

        with self._lock:
            return dict(self._stats, nodes=len(self._nodes), status=self._status)

    def body(self, source_label):
        """Return (version, JSON bytes) for the current state."""

        with self._lock:

            if self._cached_version == self._version:
                return self._version, self._cached_body

            version = self._version
            snapshot = {
                "source": source_label,
                "status": self._status,
                "version": version,
                "nodes": {node: dict(kinds) for node, kinds in self._nodes.items()},
            }

        body = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")

        with self._lock:
            if version > self._cached_version:
                self._cached_version = version
                self._cached_body = body

        return version, body

