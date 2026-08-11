# UCM Hub (Urban Climate Mesh)

## Overview

The **UCM Hub** is the central aggregation, storage, processing, and visualization platform for the Urban Climate Mesh (UCM) sensor network.

The hub is currently implemented on a **Raspberry Pi 4** running Raspberry Pi OS Trixie Lite. It provides the network services required to collect environmental measurements from distributed UCM sensor nodes, store the data, expose it through APIs, and provide web-based visualization.

UCM sensor nodes communicate with the hub over MQTT. The hub receives environmental telemetry, node metadata, and heartbeat messages and processes them through the UCM data pipeline.

The current system is designed as a small-scale operational hub that can eventually be replicated geographically or specialized for different purposes, including research and operations.

---

## System Architecture

### Data Flow

```text
┌──────────────────────────────┐
│      UCM Sensor Nodes        │
│                              │
│ ESP32-P4 + SEN54             │
│ Wi-Fi / Ethernet             │
│                              │
│ Environmental measurements   │
│ Node metadata                │
│ Heartbeats                   │
└──────────────┬───────────────┘
               │
               │ MQTT
               ▼
┌──────────────────────────────┐
│          UCM Hub             │
│       Raspberry Pi 4         │
│                              │
│        Mosquitto             │
│       MQTT Broker            │
└──────────────┬───────────────┘
               │
               │ MQTT
               ▼
┌──────────────────────────────┐
│          Telegraf            │
│                              │
│ MQTT subscription             │
│ Data parsing / transformation │
│ InfluxDB output               │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│          InfluxDB            │
│                              │
│ Time-series environmental    │
│ measurements                 │
└──────────────┬───────────────┘
               │
               ├───────────────► Grafana
               │
               ▼
┌──────────────────────────────┐
│       UCM GIS / API          │
│                              │
│ Flask API                    │
│ Node registry                │
│ Latest observations          │
│ Leaflet map interface        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        UCM Dashboard         │
│                              │
│ Nginx                        │
│ Leaflet                      │
│ Node map                     │
│ Environmental observations   │
└──────────────────────────────┘
```

---

## Hub Hardware

Current hub hardware:

* Raspberry Pi 4
* Raspberry Pi OS Trixie Lite
* Local Ethernet/Wi-Fi network connectivity
* MQTT broker
* InfluxDB time-series database
* Telegraf data pipeline
* Grafana visualization
* Nginx web server
* UCM GIS/API services

The Raspberry Pi functions as the **local aggregation point** for UCM sensor nodes.

---

## Sensor Nodes

The current UCM sensor node platform is based on:

* Waveshare ESP32-P4 development hardware
* SEN54 environmental sensor
* Wi-Fi connectivity
* Ethernet support where available
* MQTT telemetry
* Local web server
* mDNS
* Wi-Fi provisioning
* OTA firmware update infrastructure

Each physical node receives a persistent identifier derived from its hardware MAC address.

Example:

```text
UCM-E0A695
UCM-E0A6EC
UCM-E0A8DC
```

The node identifier remains stable across reboots and does not require manual configuration.

---

## MQTT Architecture

Mosquitto is the MQTT broker running on the UCM Hub.

The current topic structure is:

```text
ucm/node-<NODE_ID>/info
ucm/node-<NODE_ID>/environment
ucm/node-<NODE_ID>/heartbeat
ucm/node-<NODE_ID>/command
```

For example:

```text
ucm/node-UCM-E0A695/info
ucm/node-UCM-E0A695/environment
ucm/node-UCM-E0A695/heartbeat
ucm/node-UCM-E0A695/command
```

### Node Information

The `/info` topic provides relatively static information about a node.

Example:

```json
{
  "node": "UCM-E0A695",
  "name": "node 1",
  "description": "first node",
  "lat": 40.71280,
  "lon": -74.00600
}
```

### Environmental Data

The `/environment` topic carries sensor measurements.

Example:

```json
{
  "node": "UCM-E0A695",
  "timestamp": "2026-08-04T19:14:34Z",
  "pm1": 2.8,
  "pm25": 3.0,
  "pm4": 3.0,
  "pm10": 3.0,
  "temperature": 31.0,
  "humidity": 46.4,
  "voc": 101.0
}
```

### Heartbeat

The `/heartbeat` topic provides a lightweight indication that a node is operational.

Example:

```json
{
  "node": "UCM-E0A695",
  "timestamp": "2026-08-04T19:14:34Z",
  "status": "online"
}
```

### Commands

The `/command` topic provides a mechanism for the hub to issue commands to individual nodes.

The current firmware includes a provisioning command:

```json
{
  "command": "provision"
}
```

This allows the hub to request that a node erase its stored Wi-Fi credentials and restart into the provisioning process.

---

## MQTT Administration

To monitor all UCM MQTT traffic:

```bash
mosquitto_sub -h localhost -t "ucm/#" -v
```

To monitor commands for a specific node:

```bash
mosquitto_sub -h localhost \
  -t "ucm/node-UCM-E0A695/command" \
  -v
```

To issue a provisioning command to a node:

```bash
mosquitto_pub -h localhost \
  -t "ucm/node-UCM-E0A695/command" \
  -m '{"command":"provision"}'
```

The MQTT command hierarchy must match the node topic hierarchy exactly. MQTT wildcards are only valid in subscriptions, not when publishing.

For example, a node can subscribe to:

```text
ucm/+/command
```

but a command must be published to the concrete topic:

```text
ucm/node-UCM-E0A695/command
```

---

## Data Storage

### InfluxDB

InfluxDB provides the primary time-series storage layer for environmental measurements.

Current configuration:

```text
Organization: NYC-Mesh-Project
Bucket: Microclimate-Data
```

Measurements received through MQTT are processed by Telegraf and written into InfluxDB.

The database is intended to support:

* Real-time monitoring
* Historical environmental analysis
* Spatial comparison between nodes
* Time-series visualization
* Research datasets
* Future analytical and machine-learning workflows

---

## Telegraf

Telegraf acts as the MQTT-to-InfluxDB ingestion layer.

The basic pipeline is:

```text
MQTT
  │
  ▼
Telegraf
  │
  ▼
InfluxDB
```

Telegraf subscribes to UCM MQTT topics, parses incoming JSON payloads, and writes the resulting measurements to InfluxDB.

A previous issue involved `NaN` values in MQTT JSON payloads. Sensor firmware should therefore avoid emitting invalid JSON values and should represent unavailable measurements in a way that the ingestion pipeline can safely handle.

---

## Grafana

Grafana provides time-series visualization and analytical dashboards using InfluxDB as a data source.

Grafana can be used for:

* PM1.0 monitoring
* PM2.5 monitoring
* PM4.0 monitoring
* PM10 monitoring
* Temperature
* Relative humidity
* VOC index
* Node-level comparisons
* Historical trends
* Network monitoring

Grafana is intended primarily for analytical and operational visualization.

---

## GIS / Web Dashboard

The UCM Hub also provides a lightweight web-based geospatial interface.

The current web stack includes:

```text
Nginx
  │
  ├── Static web application
  │
  └── /api/
        │
        ▼
      Flask
        │
        ├── Node registry
        └── Latest sensor observations
```

The GIS interface uses **Leaflet** to display sensor nodes geographically.

The dashboard can provide:

* Current node locations
* Node status
* Latest sensor observations
* Node metadata
* Spatial comparison of environmental conditions

The node registry is currently maintained at:

```text
/opt/ucm-hub/gis/node_registry.json
```

The API server is currently located at:

```text
/opt/ucm-hub/gis/api_server.py
```

Nginx proxies API requests through:

```text
/api/
```

to the local Flask service.

---

## Node Discovery and Identity

Node identity is derived from the ESP32 hardware MAC address.

The current firmware generates identifiers in the form:

```text
UCM-XXXXXX
```

For example:

```text
UCM-E0A695
```

This provides a hardware-derived identifier that is:

* Unique to the physical device
* Persistent across firmware updates
* Independent of Wi-Fi configuration
* Suitable for MQTT topic naming
* Suitable for database and GIS registration

Human-readable node names and descriptions are stored separately from the hardware-derived node ID.

---

## Current Demonstrated Network

The current development network has demonstrated simultaneous operation of multiple UCM sensor nodes.

Example nodes:

```text
UCM-E0A695
UCM-E0A6EC
UCM-E0A8DC
```

All three nodes have successfully published environmental measurements and heartbeat messages through the MQTT broker.

This establishes the basic multi-node aggregation architecture.

---

## Network Architecture

The current system assumes that sensor nodes and the UCM Hub can communicate over a common IP network.

For local development this may be:

```text
ESP32 nodes
     │
     │ Wi-Fi
     ▼
Local network
     │
     ▼
UCM-HUB
```

The architecture is not dependent on a particular consumer Wi-Fi network.

The same basic model can operate over community networks, institutional networks, or other IP-based networks provided that the nodes can reach the MQTT broker.

This is particularly relevant to deployment through community networks such as NYC Mesh.

---

## Multi-Hub Architecture

The current Raspberry Pi hub is the first operational aggregation layer.

The architecture is intended to scale beyond a single hub.

A future deployment may include:

```text
                 ┌─────────────────┐
                 │ Research Hub    │
                 └────────▲────────┘
                          │
                          │
┌───────────────┐         │
│ Sensor Nodes  │         │
└───────┬───────┘         │
        │                 │
        ▼                 │
┌─────────────────┐       │
│ Operations Hub  ├───────┘
│   UCM-HUB       │
└─────────────────┘
```

The operations hub can serve as the local collection and operational monitoring point, while other hubs can subscribe to or replicate data for research, analysis, or regional aggregation.

Additional hubs may eventually be deployed when required by:

* Geographic scale
* Network topology
* Sensor population
* Processing requirements
* Research requirements
* Operational resilience

The architecture therefore treats the hub as a **replicable infrastructure component**, rather than a single permanent server.

---

## Reliability and Fault Tolerance

Reliability is an active area of development.

The current system successfully reconnects nodes to the network and MQTT broker after temporary connectivity disruptions under normal conditions.

However, MQTT publication currently does not provide complete store-and-forward protection on the sensor node.

If a node loses network or MQTT connectivity, measurements generated during the outage may currently be lost.

### Planned Node-Side Buffering

A planned improvement is local store-and-forward buffering:

```text
Sensor
  │
  ▼
Local buffer
  │
  ├── Network available ─────► MQTT
  │
  └── Network unavailable
             │
             ▼
        Store locally
             │
             ▼
      Connection restored
             │
             ▼
       Transmit backlog
```

This will allow measurements generated during temporary network outages to be retained and transmitted after connectivity is restored.

---

## OTA Firmware Updates

The sensor-node firmware uses a dual-partition OTA architecture.

The intended model is:

```text
┌───────────────┐
│ Firmware A    │
├───────────────┤
│ Firmware B    │
├───────────────┤
│ OTA metadata  │
└───────────────┘
```

The two application partitions provide the basis for safe firmware updates and rollback.

Future firmware deployment should include hardware compatibility checks so that firmware intended for one node hardware revision cannot accidentally be installed on an incompatible device.

---

## Security Considerations

The current development system operates on trusted local networks and uses unencrypted MQTT on port `1883`.

This is appropriate for the current development and field-testing environment but is **not yet a production security architecture**.

Future deployments should consider:

* MQTT authentication
* Per-node credentials
* TLS encryption
* Network segmentation
* Secure OTA updates
* Firmware signing
* Access control for administrative commands
* Hub authentication
* Protection of the provisioning mechanism

The provisioning command in particular should not remain unauthenticated when the system is deployed on an untrusted network.

---

## Operational Commands

### Check MQTT service

```bash
sudo systemctl status mosquitto
```

### Follow MQTT broker logs

```bash
sudo journalctl -u mosquitto -f
```

### Monitor all UCM MQTT traffic

```bash
mosquitto_sub -h localhost -t "ucm/#" -v
```

### Check the web/API service

```bash
curl http://localhost/api/latest
```

### Check listening services

```bash
sudo ss -lntp
```

---

## Development Status

The following core components are operational:

* ESP32-P4 sensor-node firmware
* SEN54 environmental sensing
* Wi-Fi connectivity
* Ethernet support
* Wi-Fi provisioning infrastructure
* mDNS
* MQTT telemetry
* MQTT node metadata
* MQTT heartbeat
* MQTT command infrastructure
* Raspberry Pi MQTT broker
* Telegraf ingestion
* InfluxDB storage
* Grafana visualization
* Flask API
* Node registry
* Nginx web serving
* Leaflet-based geospatial visualization
* Multi-node operation

Active development areas include:

* Node-side store-and-forward buffering
* Robust MQTT/network reconnection
* OTA firmware deployment
* Firmware/hardware compatibility checks
* Production MQTT security
* Multi-hub architecture
* Expanded GIS functionality
* Field deployment and testing

---

## Design Principles

The UCM Hub is designed around several principles:

1. **Distributed sensing**
   Environmental observations originate at inexpensive, distributed sensor nodes.

2. **Local aggregation**
   Data should be collected and made useful close to where it is generated.

3. **Open infrastructure**
   The system relies on widely available open-source technologies and documented interfaces.

4. **Interoperability**
   MQTT provides a simple messaging layer between sensor nodes and infrastructure.

5. **Scalability through replication**
   Additional hubs can be deployed rather than requiring a single centralized server.

6. **Resilience**
   Nodes and hubs should continue operating through temporary network failures whenever possible.

7. **Research usability**
   Operational data should remain accessible for visualization, analysis, and interdisciplinary research.

8. **Community deployment**
   The architecture is intended to operate on networks outside conventional institutional infrastructure, including community networks.

---

## Project Structure

The UCM system is currently organized into two principal software repositories:

```text
UCM Development Project
│
├── ucm-node
│   └── ESP32-P4 sensor-node firmware
│
└── ucm-hub
    └── Raspberry Pi hub software
```

The `ucm-node` repository contains the embedded firmware running on UCM sensor nodes.

The `ucm-hub` repository contains the software, configuration, services, APIs, dashboards, and infrastructure required to operate a UCM aggregation hub.

---

## Project Status

The UCM Hub has progressed from a prototype data collector to a functioning multi-node environmental sensing platform.

The current development priority is to move from a **working prototype** toward a **field-ready distributed sensing system**, with particular emphasis on reliability, OTA management, fault tolerance, security, and deployment across community networks.

The immediate field-testing objective is to validate operation of the complete system outside the development environment, including sensor nodes, network connectivity, MQTT transport, hub services, data ingestion, visualization, and recovery from network interruptions.
