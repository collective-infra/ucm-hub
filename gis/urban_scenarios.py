import paho.mqtt.client as mqtt
import json
import time
import sys
import math

BROKER = "192.168.1.236"

# The full registry of simulation nodes
SIM_NODES = {
    "node-sim-01": {"lat": 40.877, "label": "Williamsbridge (BX)", "type": "residential"},
    "node-sim-02": {"lat": 40.854, "label": "Belmont (BX)", "type": "residential"},
    "node-sim-03": {"lat": 40.843, "label": "West Farms (BX)", "type": "residential"},
    "node-sim-04": {"lat": 40.837, "label": "Highbridge (BX)", "type": "residential"},
    "node-sim-05": {"lat": 40.809, "label": "Hunts Point (BX)", "type": "industrial"},
    "node-sim-06": {"lat": 40.807, "label": "Mott Haven (BX)", "type": "industrial"},
    "node-sim-07": {"lat": 40.795, "label": "East Harlem (MN)", "type": "dense-urban"},
    "node-sim-08": {"lat": 40.812, "label": "Central Harlem (MN)", "type": "dense-urban"},
    "node-sim-09": {"lat": 40.772, "label": "Astoria (QN)", "type": "residential"},
    "node-sim-10": {"lat": 40.748, "label": "Long Island City (QN)", "type": "dense-urban"},
    "node-sim-11": {"lat": 40.730, "label": "Greenpoint (BK)", "type": "dense-urban"},
    "node-sim-12": {"lat": 40.694, "label": "Bushwick (BK)", "type": "residential"},
    "node-sim-13": {"lat": 40.683, "label": "Bed-Stuy (BK)", "type": "residential"},
    "node-sim-14": {"lat": 40.665, "label": "Brownsville (BK)", "type": "residential"},
    "node-sim-15": {"lat": 40.645, "label": "Sunset Park (BK)", "type": "industrial"}
}

def get_scenario_payload(scenario, node_id, info, tick):
    # Baseline "Clean Air"
    p = {"pm25": 12.0, "temp": 22.0, "rh": 45.0, "voc": 50, "nox": 5}
    
    if scenario == "wildfire":
        # Wildfire logic: Plume moves South over 48 ticks
        north_ref = 40.9
        plume_lat = north_ref - (tick * 0.012)
        dist = abs(info['lat'] - plume_lat)
        intensity = 450 * (0.5 ** (dist / 0.05))
        p["pm25"] = max(12.0, round(intensity, 2))
        p["voc"] = 100 + (p["pm25"] * 0.5)

    elif scenario == "heatwave":
        # Heatwave logic: Temp builds over time, peaking in dense-urban areas
        diurnal_effect = math.sin(tick / 10) * 5
        p["temp"] = 28 + diurnal_effect + (4 if info['type'] == "dense-urban" else 0)
        p["rh"] = 40 - diurnal_effect
        p["voc"] = 150 if info['type'] == "dense-urban" else 80

    elif scenario == "traffic":
        # Traffic logic: Peaks in industrial zones
        peak_mult = 1.5 if (tick % 24 in [8, 9, 17, 18]) else 0.5
        if info['type'] == "industrial":
            p["pm25"] = 35 * peak_mult
            p["nox"] = 90 * peak_mult
            p["voc"] = 200 * peak_mult
            
    return p

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 urban_scenarios.py [wildfire|heatwave|traffic]")
        return

    mode = sys.argv[1]
    client = mqtt.Client()
    client.connect(BROKER)
    
    tick = 0
    while True:
        for node_id, info in SIM_NODES.items():
            payload = get_scenario_payload(mode, node_id, info, tick)
            payload["label"] = info['label']
            client.publish(f"ucm/{node_id}/environment", json.dumps(payload))
        
        print(f"[{mode.upper()}] Tick {tick} published to all nodes.")
        tick += 1
        time.sleep(3) # Slowed down to give the map UI breathing room

if __name__ == "__main__":
    main()
