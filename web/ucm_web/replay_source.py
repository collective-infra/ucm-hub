import json
import logging
import threading
import time
from datetime import datetime, timezone


# ---------------- REPLAY SOURCE ----------------
#
# Replays recorded readings from a pg_dump of the sn3 Timescale database
# (environment_readings + sensors), turned back into the payloads the
# firmware publishes, so the site can be tried against real data without
# being on the mesh. The dump has no heartbeats, so none are replayed.

log = logging.getLogger(__name__)

READING_COLUMNS = ("time", "node_id", "temperature_c", "humidity_percent",
                   "pm1", "pm25", "pm10", "voc", "received_at", "pm4")
SENSOR_COLUMNS = ("node_id", "display_name", "lat", "lon", "contact_point", "created_at")


def parse_dump(path):
    """Return (readings sorted by time, sensors) from a pg_dump .sql file."""

    readings = {}
    sensors = []
    columns = None
    target = None

    with open(path, encoding="utf-8", errors="replace") as dump:
        for line in dump:

            if target is None:
                if not line.startswith("COPY "):
                    continue
                table = line.split()[1]
                columns = tuple(c.strip(' "') for c in
                                line[line.index("(") + 1:line.index(")")].split(","))
                # Readings live in the hypertable chunks and the parent table.
                if table.endswith("environment_readings") or "_hyper_" in table:
                    target = "readings"
                elif table == "public.sensors":
                    target = "sensors"
                else:
                    target = "skip"
                continue

            if line.startswith("\\."):
                target = None
                continue
            if target == "skip":
                continue

            row = dict(zip(columns, (None if v == "\\N" else v
                                     for v in line.rstrip("\n").split("\t"))))

            if target == "sensors":
                sensors.append(row)
            else:
                try:
                    when = parse_time(row["time"])
                except (KeyError, ValueError):
                    continue
                # Chunks and the parent table can repeat a row; keep one.
                readings[(when, row["node_id"])] = row

    ordered = [(when, row) for (when, _), row in sorted(readings.items(),
                                                       key=lambda item: item[0])]
    return ordered, sensors


def parse_time(text):
    # pg_dump writes offsets like "-04"; fromisoformat wants "-04:00".
    if len(text) >= 3 and text[-3] in "+-" and text[-2:].isdigit():
        text += ":00"
    return datetime.fromisoformat(text)


def number(value):
    if value is None:
        return None
    result = float(value)
    return int(result) if result.is_integer() else result


def environment_payload(when, row):
    return json.dumps({
        "node": row["node_id"],
        "timestamp": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pm1": number(row.get("pm1")),
        "pm25": number(row.get("pm25")),
        "pm4": number(row.get("pm4")),
        "pm10": number(row.get("pm10")),
        "temperature": number(row.get("temperature_c")),
        "humidity": number(row.get("humidity_percent")),
        "voc": number(row.get("voc")),
    }).encode()


def start(config, store):

    readings, sensors = parse_dump(config.replay_path)
    if not readings:
        raise SystemExit(f"no environment readings found in {config.replay_path}")

    for sensor in sensors:
        node_id = sensor["node_id"]
        store.record(f"ucm/node-{node_id}/status",
                     json.dumps({"node": node_id, "status": "online"}).encode())
        store.record(f"ucm/node-{node_id}/info", json.dumps({
            "node": node_id,
            "name": sensor.get("display_name"),
            "description": sensor.get("contact_point"),
            "lat": number(sensor.get("lat")),
            "lon": number(sensor.get("lon")),
        }).encode())

    store.set_status(
        f"replaying {len(readings):,} readings from {readings[0][0]:%Y-%m-%d} "
        f"to {readings[-1][0]:%Y-%m-%d} at {config.replay_speed:g}x "
        f"(gaps capped at {config.replay_max_gap:g} s)"
    )

    def run():
        while True:
            previous = None
            for when, row in readings:
                if previous is not None:
                    gap = (when - previous).total_seconds() / config.replay_speed
                    time.sleep(min(max(gap, 0.0), config.replay_max_gap))
                previous = when
                try:
                    store.record(f"ucm/node-{row['node_id']}/environment",
                                 environment_payload(when, row))
                except Exception:
                    log.exception("replay record failed")
            log.info("replay finished, starting over")

    thread = threading.Thread(target=run, name="replay-source", daemon=True)
    thread.start()
    return thread
