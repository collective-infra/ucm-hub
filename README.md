Good—do this on the **hub repo first**, because it’s your infrastructure backbone.

Below is a clean, deployment-grade `README.md` you can drop into `/opt/ucm-hub`.

---

# 📄 UCM Hub README

```markdown
# UCM Hub (Urban Climate Mesh)

## Overview

The UCM Hub is the central aggregation and visualization system for the Urban Climate Mesh sensor network. It receives environmental telemetry from distributed Raspberry Pi sensor nodes via MQTT, stores time-series data in InfluxDB, processes streams with Telegraf, and exposes visualization dashboards via Grafana and a Leaflet-based geospatial interface.

---

## System Architecture

### Data Flow

```

Sensor Nodes (ESP32 / Raspberry Pi + SEN54)
↓ MQTT
Mosquitto Broker (Hub)
↓
Telegraf
↓
InfluxDB (Time Series Storage)
↓
Grafana / Queries / Analysis
↓
Leaflet (Geospatial Visualization)
↓
Nginx (Web Interface)

```

---

## Hub Environment

- Hostname: UCM-HUB
- IP Address: 192.168.1.236
- OS: Trixie OS Lite

---

## Core Services

| Service     | Purpose                          |
|------------|----------------------------------|
| Mosquitto  | MQTT message broker              |
| InfluxDB   | Time-series database             |
| Telegraf   | Data ingestion pipeline          |
| Grafana    | Visualization & dashboards       |
| Nginx      | Web server / reverse proxy       |
| Leaflet    | Mapping / geospatial UI layer    |

---

## InfluxDB Configuration

- Organization: NYC-Mesh-Project
- Bucket: Microclimate-Data

---

## Repository Structure

```

/opt/ucm-hub/
├── mqtt/
│   └── mosquitto.conf
├── influxdb/
│   └── config.toml
├── telegraf/
│   └── telegraf.conf
├── nginx/
│   ├── nginx.conf
│   └── sites-available/
├── grafana/
├── README.md

````

---

## Deployment Requirements

### Install Dependencies

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients influxdb telegraf nginx grafana -y
````

---

## Service Management

### Start all services

```bash
sudo systemctl start mosquitto
sudo systemctl start influxdb
sudo systemctl start telegraf
sudo systemctl start nginx
sudo systemctl start grafana-server
```

### Enable on boot

```bash
sudo systemctl enable mosquitto
sudo systemctl enable influxdb
sudo systemctl enable telegraf
sudo systemctl enable nginx
sudo systemctl enable grafana-server
```

---

## MQTT Topics (Standard Schema)

```
ucm/node/{node_id}/temperature
ucm/node/{node_id}/humidity
ucm/node/{node_id}/pm25
ucm/node/{node_id}/pm10
ucm/node/{node_id}/timestamp
```

---

## Data Format (Recommended Payload)

```json
{
  "node_id": "node-01",
  "timestamp": "ISO-8601",
  "temperature": 23.1,
  "humidity": 41.2,
  "pm25": 7.2
}
```

---

## Operational Checks

### MQTT Live Feed

```bash
mosquitto_sub -h localhost -t "#" -v
```

### InfluxDB Query

```bash
influx query 'from(bucket:"Microclimate-Data") |> range(start: -10m)'
```

### Service Status

```bash
systemctl status mosquitto
systemctl status influxdb
systemctl status telegraf
```

---

## Reboot Validation Checklist

After reboot:

* MQTT broker running
* Telegraf connected to InfluxDB
* Grafana accessible
* Node data streaming active

---

## Notes

* This hub is the aggregation point for all UCM sensor nodes.
* Configuration files are version-controlled for reproducibility.
* Data schema consistency across nodes is critical for system integrity.

````



