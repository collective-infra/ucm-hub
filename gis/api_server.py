from flask import Flask, jsonify
from flask_cors import CORS # 1. Add this import
from influxdb_client import InfluxDBClient

import json

app = Flask(__name__)
CORS(app) # 2. Add this line right here
# ---------------- CONFIG ----------------

URL = "http://localhost:8086"
TOKEN = "bQD57FX3f-0Yz17lImhqxLcdOiQ4wnMqIzM40tOoMfaPI-Kyxv53ZiGERPFP8n71VEjvg1Nk0l0RzppVmSskeA=="
ORG = "NYC-Mesh-Project"
BUCKET = "Microclimate-Data"

NODE_REGISTRY_FILE = "/opt/ucm-hub/gis/node_registry.json"


# ---------------- LOAD NODE REGISTRY ----------------

def load_node_registry():
    try:
        with open(NODE_REGISTRY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("Registry load error:", e)
        return {}


# ---------------- API ROUTE ----------------

@app.route('/api/latest')
def latest_data():

    node_registry = load_node_registry()

    client = InfluxDBClient(
        url=URL,
        token=TOKEN,
        org=ORG
    )

    query_api = client.query_api()
    flux_query = f'''
    from(bucket: "{BUCKET}")
        |> range(start: -15m)
        |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
        |> group(columns: ["topic", "_field"])
        |> last()
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''

    tables = query_api.query(flux_query)

    features = []

    for table in tables:
        for record in table.records:

            values = record.values

            # ---------------- NODE ID FROM TOPIC ----------------
            topic = values.get("topic", "")
            parts = topic.split("/")

            if len(parts) >= 2:
                node_id = parts[1].replace("node-", "")
            else:
                continue

            # ---------------- LOCATION LOOKUP ----------------
            loc = node_registry.get(node_id)
            if not loc:
                continue

            lat = loc.get("lat")
            lon = loc.get("lon")

            if lat is None or lon is None:
                continue

            # ---------------- FEATURE BUILD ----------------
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "node": node_id,
                    "label": loc.get("label"),

                    "timestamp": values.get("_time").isoformat()
                    if values.get("_time") else None,

                    # Particle measurements
                    "pm1": values.get("pm1"),
                    "pm2_5": values.get("pm25"),
                    "pm4": values.get("pm4"),
                    "pm10": values.get("pm10"),

                    # Environment
                    "temp": values.get("temperature"),
                    "rh": values.get("humidity"),

                    # Air quality indices
                    "voc_index": values.get("voc"),
                    "nox_index": values.get("nox")
                }
            }

            features.append(feature)

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })


# ---------------- START SERVER ----------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
