#!/usr/bin/env python3

import json
import os
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

MQTT_HOST = "localhost"
MQTT_PORT = 1883

REGISTRY_FILE = Path(
    "/opt/ucm-hub/gis/node_registry.new.json"
)

INACTIVE_AFTER = timedelta(hours=24)

INFO_TOPIC = "ucm/+/info"
HEARTBEAT_TOPIC = "ucm/+/heartbeat"


# --------------------------------------------------
# GLOBAL STATE
# --------------------------------------------------

registry = {}
dirty = False
running = True


# --------------------------------------------------
# TIME
# --------------------------------------------------

def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def parse_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None


# --------------------------------------------------
# REGISTRY
# --------------------------------------------------

def load_registry():

    global registry

    try:
        with open(REGISTRY_FILE, "r") as f:
            registry = json.load(f)

    except Exception as e:
        print(f"ERROR loading registry: {e}")
        sys.exit(1)

    if "nodes" not in registry:
        print("ERROR: Registry does not contain 'nodes'")
        sys.exit(1)

    print(
        f"Loaded registry: "
        f"{len(registry['nodes'])} nodes"
    )


def save_registry():

    global dirty

    if not dirty:
        return

    registry["updated_at"] = iso(now())

    tmp_file = REGISTRY_FILE.with_suffix(
        REGISTRY_FILE.suffix + ".tmp"
    )

    try:

        with open(tmp_file, "w") as f:
            json.dump(
                registry,
                f,
                indent=2
            )
            f.write("\n")

        os.replace(tmp_file, REGISTRY_FILE)

        dirty = False

        print(
            f"Registry updated: {REGISTRY_FILE}"
        )

    except Exception as e:

        print(
            f"ERROR writing registry: {e}"
        )

        try:
            tmp_file.unlink()
        except FileNotFoundError:
            pass


# --------------------------------------------------
# NODE LOOKUP
# --------------------------------------------------

def get_node(node_id):

    return registry["nodes"].get(node_id)


# --------------------------------------------------
# INFO MESSAGE
# --------------------------------------------------

def process_info(node_id, payload):

    global dirty

    node = get_node(node_id)

    if node is None:

        print(
            f"INFO ignored: unregistered node "
            f"{node_id}"
        )

        return

    try:
        data = json.loads(payload)

    except json.JSONDecodeError:

        print(
            f"Invalid JSON from {node_id} "
            f"on info topic"
        )

        return

    site = node.setdefault("site", {})

    changed = False

    # ----------------------------------------------
    # Node name
    # ----------------------------------------------

    if "name" in data:
        if site.get("name") != data["name"]:
            site["name"] = data["name"]
            changed = True

    # ----------------------------------------------
    # Description
    # ----------------------------------------------

    if "description" in data:
        if site.get("description") != data["description"]:
            site["description"] = data["description"]
            changed = True

    # ----------------------------------------------
    # Latitude
    # ----------------------------------------------

    if "lat" in data:
        if site.get("latitude") != data["lat"]:
            site["latitude"] = data["lat"]
            changed = True

    # ----------------------------------------------
    # Longitude
    # ----------------------------------------------

    if "lon" in data:
        if site.get("longitude") != data["lon"]:
            site["longitude"] = data["lon"]
            changed = True

    if changed:

        dirty = True

        print(
            f"INFO updated: {node_id}"
        )

    else:

        print(
            f"INFO received: {node_id}"
        )


# --------------------------------------------------
# HEARTBEAT
# --------------------------------------------------

def process_heartbeat(node_id, payload):

    global dirty

    node = get_node(node_id)

    if node is None:

        print(
            f"HEARTBEAT ignored: "
            f"unregistered node {node_id}"
        )

        return

    try:
        data = json.loads(payload)

    except json.JSONDecodeError:

        print(
            f"Invalid JSON from {node_id} "
            f"on heartbeat topic"
        )

        return

    runtime = node.setdefault(
        "runtime",
        {}
    )

    timestamp = data.get("timestamp")

    heartbeat_time = parse_time(timestamp)

    if heartbeat_time is None:
        heartbeat_time = now()

    timestamp_string = iso(heartbeat_time)

    # ----------------------------------------------
    # First seen
    # ----------------------------------------------

    if not runtime.get("first_seen"):

        runtime["first_seen"] = timestamp_string

        print(
            f"FIRST SEEN: {node_id} "
            f"{timestamp_string}"
        )

        dirty = True

    # ----------------------------------------------
    # Last seen
    # ----------------------------------------------

    if runtime.get("last_seen") != timestamp_string:

        runtime["last_seen"] = timestamp_string

        dirty = True

    # ----------------------------------------------
    # Active
    # ----------------------------------------------

    if runtime.get("status") != "ACTIVE":

        runtime["status"] = "ACTIVE"

        print(
            f"ACTIVE: {node_id}"
        )

        dirty = True


# --------------------------------------------------
# INACTIVE CHECK
# --------------------------------------------------

def update_inactive_nodes():

    global dirty

    current_time = now()

    for node_id, node in registry["nodes"].items():

        # Simulated nodes aren't governed by
        # heartbeat status.

        if node.get("metadata", {}).get("simulated"):
            continue

        runtime = node.setdefault(
            "runtime",
            {}
        )

        last_seen = parse_time(
            runtime.get("last_seen")
        )

        if last_seen is None:
            continue

        age = current_time - last_seen

        if age > INACTIVE_AFTER:

            if runtime.get("status") != "INACTIVE":

                runtime["status"] = "INACTIVE"

                print(
                    f"INACTIVE: {node_id} "
                    f"(last seen {age} ago)"
                )

                dirty = True


# --------------------------------------------------
# MQTT
# --------------------------------------------------

def on_connect(client, userdata, flags, rc):

    if rc != 0:

        print(
            f"MQTT connection failed: rc={rc}"
        )

        return

    print(
        f"Connected to MQTT broker "
        f"{MQTT_HOST}:{MQTT_PORT}"
    )

    client.subscribe(INFO_TOPIC)
    client.subscribe(HEARTBEAT_TOPIC)

    print(f"Subscribed: {INFO_TOPIC}")
    print(f"Subscribed: {HEARTBEAT_TOPIC}")


def on_message(client, userdata, msg):

    topic = msg.topic

    payload = msg.payload.decode(
        "utf-8",
        errors="replace"
    )

    parts = topic.split("/")

    if len(parts) != 3:
        return

    node_part = parts[1]

    if not node_part.startswith("node-"):
        return

    node_id = node_part[5:]

    message_type = parts[2]

    if message_type == "info":

        process_info(
            node_id,
            payload
        )

    elif message_type == "heartbeat":

        process_heartbeat(
            node_id,
            payload
        )


# --------------------------------------------------
# SHUTDOWN
# --------------------------------------------------

def shutdown(signum, frame):

    global running

    print()
    print("Shutting down registry manager...")

    running = False


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    load_registry()

    signal.signal(
        signal.SIGINT,
        shutdown
    )

    signal.signal(
        signal.SIGTERM,
        shutdown
    )

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1
    )

    client.on_connect = on_connect
    client.on_message = on_message

    print(
        f"Connecting to MQTT "
        f"{MQTT_HOST}:{MQTT_PORT}"
    )

    client.connect(
        MQTT_HOST,
        MQTT_PORT,
        60
    )

    client.loop_start()

    try:

        while running:

            update_inactive_nodes()
            save_registry()

            time.sleep(5)

    finally:

        client.loop_stop()
        client.disconnect()

        save_registry()

        print(
            "Registry manager stopped."
        )


if __name__ == "__main__":
    main()
