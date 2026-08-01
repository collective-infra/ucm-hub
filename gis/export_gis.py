import json
import os
from influxdb_client import InfluxDBClient


# ---------------- CONFIG ----------------

URL = "http://localhost:8086"
TOKEN = "bQD57FX3f-0Yz17lImhqxLcdOiQ4wnMqIzM40tOoMfaPI-Kyxv53ZiGERPFP8n71VEjvg1Nk0l0RzppVmSskeA=="
ORG = "NYC-Mesh-Project"
BUCKET = "Microclimate-Data"

OUTPUT_FILE = "/opt/ucm-hub/gis/ucm_latest.geojson"
NODE_REGISTRY_FILE = "/opt/ucm-hub/gis/node_registry.json"


# ---------------- LOAD NODE REGISTRY ----------------

def load_node_registry():
    try:
        with open(NODE_REGISTRY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("ERROR loading node registry:", e)
        return {}


# ---------------- EXPORT FUNCTION ----------------

def get_gis_data():
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    query_api = client.query_api()

    node_registry = load_node_registry()

    # FIXED QUERY:
    # - removed pivot()
    # - removed invalid last() usage after reshape
    flux_query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -15m)
      |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
      |> last()
    '''

    tables = query_api.query(flux_query)

    features = []

    for table in tables:
        for record in table.records:

            values = record.values

            node_id = values.get("node_id") or values.get("node")

            if not node_id:
                continue

            # ---------------- NODE LOCATION LOOKUP ----------------
            loc = node_registry.get(node_id)

            if not loc:
                continue

            lat = loc.get("lat")
            lon = loc.get("lon")

            if lat is None or lon is None:
                continue

            # ---------------- BUILD FEATURE ----------------
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "node_id": node_id,
                    "label": loc.get("label"),

                    "timestamp": values.get("_time").isoformat()
                    if values.get("_time") else None,

                    # PARTICULATE MATTER
                    "pm1": values.get("pm1"),
                    "pm25": values.get("pm25"),
                    "pm4": values.get("pm4"),
                    "pm10": values.get("pm10"),

                    # ENVIRONMENT
                    "temp": values.get("temp"),
                    "rh": values.get("rh"),

                    # GASES
                    "voc_index": values.get("voc_index"),
                    "nox_index": values.get("nox_index")
                }
            }

            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # ---------------- ATOMIC WRITE ----------------
    tmp_file = OUTPUT_FILE + ".tmp"

    try:
        with open(tmp_file, "w") as f:
            json.dump(geojson, f, indent=2)

        os.replace(tmp_file, OUTPUT_FILE)

        print(f"Updated GeoJSON → {OUTPUT_FILE}")

    except Exception as e:
        print("ERROR writing GeoJSON:", e)


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    get_gis_data()
