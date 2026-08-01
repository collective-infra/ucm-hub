import paho.mqtt.client as mqtt
import json
import time

# UCM Hub Configuration matching your API server
BROKER = "192.168.1.236"

# Ensure these match the keys in /opt/ucm-hub/gis/node_registry.json
SIM_NODES = {
    "node-sim-01": {"lat": 40.877, "label": "Williamsbridge (BX)"},
    "node-sim-02": {"lat": 40.854, "label": "Belmont (BX)"},
    "node-sim-03": {"lat": 40.843, "label": "West Farms (BX)"},
    "node-sim-04": {"lat": 40.837, "label": "Highbridge (BX)"},
    "node-sim-05": {"lat": 40.809, "label": "Hunts Point (BX)"},
    "node-sim-06": {"lat": 40.807, "label": "Mott Haven (BX)"},
    "node-sim-07": {"lat": 40.795, "label": "East Harlem (MN)"},
    "node-sim-08": {"lat": 40.812, "label": "Central Harlem (MN)"},
    "node-sim-09": {"lat": 40.772, "label": "Astoria (QN)"},
    "node-sim-10": {"lat": 40.748, "label": "Long Island City (QN)"},
    "node-sim-11": {"lat": 40.730, "label": "Greenpoint (BK)"},
    "node-sim-12": {"lat": 40.694, "label": "Bushwick (BK)"},
    "node-sim-13": {"lat": 40.683, "label": "Bed-Stuy (BK)"},
    "node-sim-14": {"lat": 40.665, "label": "Brownsville (BK)"},
    "node-sim-15": {"lat": 40.645, "label": "Sunset Park (BK)"}
}

def calculate_pollution(lat, sim_hour):
    north_ref = 40.9
    plume_front_lat = north_ref - (sim_hour * 0.012)
    dist = abs(lat - plume_front_lat)
    intensity = 450 * (0.5 ** (dist / 0.05)) 
    return max(12.0, round(intensity, 2))

client = mqtt.Client()
client.connect(BROKER)

for hr in range(48):
    for node_id, data in SIM_NODES.items():
        pm_val = calculate_pollution(data['lat'], hr)
        
        # ALIGNED PAYLOAD:
        # 1. Used 'pm25' (no dot) so Telegraf matches your API lookup
        # 2. Used 'rh' instead of 'humidity'
        payload = {
            "pm1": round(pm_val * 0.8, 2),
            "pm25": pm_val, 
            "pm4": round(pm_val * 1.1, 2),
            "pm10": round(pm_val * 1.3, 2),
            "temp": 24.0,
            "rh": 42.0, 
            "voc_index": 100,
            "nox_index": 1,
            "label": data['label']
        }
        
        client.publish(f"ucm/{node_id}/environment", json.dumps(payload))
        
    print(f"Hour {hr} published.")
    time.sleep(2) 

client.disconnect()
