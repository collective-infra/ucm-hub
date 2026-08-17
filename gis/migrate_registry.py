#!/usr/bin/env python3

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


REGISTRY_FILE = Path("/opt/ucm-hub/gis/node_registry.json")
BACKUP_FILE = Path("/opt/ucm-hub/gis/node_registry.json.pre_migration")
OUTPUT_FILE = Path("/opt/ucm-hub/gis/node_registry.new.json")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def migrate_node(node_id, old):

    # Simulated nodes are retained, but explicitly identified.
    simulated = node_id.startswith("node-sim-")

    first_seen = old.get("first_seen")
    last_seen = old.get("last_seen")

    if simulated:
        runtime_status = "SIMULATED"
    elif last_seen:
        runtime_status = "ACTIVE"
    else:
        runtime_status = "NOT_SEEN"

    node = {
        "node_id": node_id,

        "lifecycle": {
            "status": "REGISTERED",
            "registered_at": None
        },

        "runtime": {
            "status": runtime_status,
            "first_seen": first_seen,
            "last_seen": last_seen
        },

        "site": {
            "name": old.get("label", ""),
            "description": old.get("description", ""),
            "latitude": old.get("lat"),
            "longitude": old.get("lon"),
            "elevation": old.get("elevation")
        },

        "hardware": {
            "platform": old.get("platform"),
            "sensor": old.get("sensor")
        },

        "deployment": {
            "organization": old.get("organization", ""),
            "location_description": old.get(
                "location_description",
                old.get("description", "")
            ),
            "deployed_at": old.get("deployed_at")
        },

        "test": {
            "status": old.get("test_status"),
            "tested_at": old.get("tested_at"),
            "firmware": old.get("firmware", "")
        },

        "metadata": {
            "notes": old.get("notes", ""),
            "simulated": simulated
        }
    }

    return node


def main():

    if not REGISTRY_FILE.exists():
        print(f"ERROR: Registry not found: {REGISTRY_FILE}")
        return 1

    if BACKUP_FILE.exists():
        print(f"ERROR: Backup already exists: {BACKUP_FILE}")
        print("Refusing to overwrite an existing backup.")
        return 1

    print(f"Reading: {REGISTRY_FILE}")

    with open(REGISTRY_FILE, "r") as f:
        old_registry = json.load(f)

    if "nodes" in old_registry:
        print("Registry already appears to use the new format.")
        return 1

    if not isinstance(old_registry, dict):
        print("ERROR: Registry is not a JSON object.")
        return 1

    # Preserve the original file.
    shutil.copy2(REGISTRY_FILE, BACKUP_FILE)

    new_registry = {
        "version": 1,
        "updated_at": now_iso(),
        "nodes": {}
    }

    for node_id, old_node in old_registry.items():

        if not isinstance(old_node, dict):
            print(f"WARNING: Skipping invalid node entry: {node_id}")
            continue

        new_registry["nodes"][node_id] = migrate_node(
            node_id,
            old_node
        )

    with open(OUTPUT_FILE, "w") as f:
        json.dump(new_registry, f, indent=2)
        f.write("\n")

    print()
    print("Migration complete.")
    print()
    print(f"Original: {REGISTRY_FILE}")
    print(f"Backup:   {BACKUP_FILE}")
    print(f"New file: {OUTPUT_FILE}")
    print()
    print(f"Nodes migrated: {len(new_registry['nodes'])}")
    print()
    print("IMPORTANT:")
    print("The original registry has NOT been replaced.")
    print("Review the new file before installing it.")


if __name__ == "__main__":
    raise SystemExit(main())
