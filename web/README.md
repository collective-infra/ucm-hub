# UCM raw sensor feed

A minimal web page that shows the latest raw MQTT payload from every UCM node, as plain text. There is no database: the server subscribes to `ucm/+/environment`, `info` and `status` and keeps only the newest message per node and topic in memory.

## Run

```bash
cd web
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Fake nodes, works anywhere
UCM_MOCK=1 .venv/bin/python run.py

# Recorded readings from a pg_dump of the sn3 Timescale DB (dumps are gitignored)
UCM_REPLAY=../nycmesh/meshroom-vm-oct-12-a.sql UCM_REPLAY_SPEED=60 .venv/bin/python run.py

# Real broker (nyit-ucm.nycmesh.net only resolves on the mesh)
.venv/bin/python run.py
```

Open http://localhost:5002. `/healthz` shows message counters and broker status.

## Layout

```
web/
├── run.py                  entry point: config, data source, waitress server
├── ucm_web/
│   ├── config.py           all settings, read from environment variables
│   ├── store.py            thread-safe latest-value store with size limits
│   ├── mqtt_source.py      MQTT subscriber (auto-reconnect, never crashes on bad messages)
│   ├── mock_source.py      fake nodes at a configurable rate
│   ├── replay_source.py    replays environment_readings + sensors from a DB dump
│   ├── app.py              Flask routes: /, /api/raw, /healthz
│   └── static/index.html   the page
└── tests/
    ├── test_feed.py        unit tests (pytest)
    └── load_test.py        simulated viewers against a running server
```

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `UCM_MQTT_HOST` / `UCM_MQTT_PORT` | `nyit-ucm.nycmesh.net` / `1883` | |
| `UCM_MQTT_USER` / `UCM_MQTT_PASSWORD` | unset | Anonymous is allowed temporarily by the broker ACL |
| `UCM_MOCK` | unset | `1` generates fake readings instead of using MQTT |
| `UCM_MOCK_NODES` / `UCM_MOCK_HZ` | `15` / `1` | Fake node count and messages per second per node |
| `UCM_REPLAY` | unset | Path to a `.sql` dump to replay as firmware-shaped payloads |
| `UCM_REPLAY_SPEED` / `UCM_REPLAY_MAX_GAP` | `1` / `5` | Playback speed, and the longest pause between readings in seconds |
| `UCM_WEB_HOST` / `UCM_WEB_PORT` | `127.0.0.1` / `5002` | Use `0.0.0.0` to serve other machines |
| `UCM_WEB_THREADS` | `8` | waitress worker threads |
| `UCM_MAX_NODES` / `UCM_MAX_PAYLOAD_BYTES` | `200` / `4096` | Messages beyond these are dropped and counted |

## Why it does not fall over under load

- **Bounded memory.** Only the latest message per node and topic is kept. Unknown topic shapes, oversized payloads and node IDs beyond `UCM_MAX_NODES` are dropped and counted in `/healthz`. This matters because the broker currently accepts anonymous publishers.
- **The MQTT thread cannot die.** Every paho callback catches its own exceptions. A crash inside a callback would otherwise stop the network thread and freeze the feed. Reconnects back off from 1 to 30 s.
- **Cheap reads.** The JSON response is built once per change and shared by all viewers. Browsers send `If-None-Match`, and the server answers `304` with no body when nothing changed.
- **Production server.** waitress with a fixed thread pool replaces Flask's dev server, so a burst of viewers queues instead of spawning unbounded threads.
- **Gentle browser.** One request at a time, backoff to 30 s while the server is unreachable, and text updated in place (no flicker).

Load test on a laptop, with 50 simulated viewers polling every 0.2 s for 30 s:

| Feed rate | Requests | Errors | Median / p95 latency | Memory |
| --- | --- | --- | --- | --- |
| 15 nodes × 1 msg/s (expected) | 7,226 | 0 | 3.6 / 10.0 ms | ~21–31 MB, flat |
| 15 nodes × 50 msg/s | 7,161 | 0 | 4.7 / 13.4 ms | ~27–31 MB, flat |

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests

# load test: start a server first
UCM_MOCK=1 UCM_MOCK_HZ=50 .venv/bin/python run.py &
.venv/bin/python tests/load_test.py --viewers 50 --seconds 30
```
