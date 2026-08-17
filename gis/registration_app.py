#!/usr/bin/env python3

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, jsonify


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

REGISTRY_FILE = Path(
    "/opt/ucm-hub/gis/node_registry.new.json"
)

HOST = "0.0.0.0"
PORT = 5001


# --------------------------------------------------
# APPLICATION
# --------------------------------------------------

app = Flask(__name__)


# --------------------------------------------------
# TIME
# --------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------
# REGISTRY
# --------------------------------------------------

def load_registry():

    with open(REGISTRY_FILE, "r") as f:
        return json.load(f)


def save_registry(registry):

    tmp_file = REGISTRY_FILE.with_suffix(
        REGISTRY_FILE.suffix + ".tmp"
    )

    with open(tmp_file, "w") as f:
        json.dump(
            registry,
            f,
            indent=2
        )
        f.write("\n")

    os.replace(tmp_file, REGISTRY_FILE)


# --------------------------------------------------
# NODE
# --------------------------------------------------

def get_node(registry, node_id):

    return registry.get("nodes", {}).get(node_id)


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route("/")
def index():

    registry = load_registry()

    nodes = registry.get("nodes", {})

    return render_template(
        "registration.html",
        nodes=nodes
    )

@app.route("/register")
def register_index():

    registry = load_registry()

    nodes = registry.get("nodes", {})

    return render_template(
        "registration_index.html",
        nodes=nodes
    )
@app.route("/register/<node_id>", methods=["GET", "POST"])
def register(node_id):

    registry = load_registry()

    node = get_node(
        registry,
        node_id
    )

    if node is None:
        return (
            f"Node {node_id} is not registered.",
            404
        )

    if request.method == "POST":


# --------------------------------------------------
# NODE TEST API
# --------------------------------------------------

@app.route("/api/node-test", methods=["POST"])
def node_test():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "JSON request body required"
        }), 400

    node_id = str(
        data.get("node_id", "")
    ).strip()

    if not node_id:
        return jsonify({
            "success": False,
            "error": "node_id required"
        }), 400

    registry = load_registry()

    node = get_node(
        registry,
        node_id
    )

    if node is None:
        return jsonify({
            "success": False,
            "error": f"Node {node_id} is not registered"
        }), 404

    passed = bool(
        data.get("passed", False)
    )

    lifecycle = node.setdefault(
        "lifecycle",
        {}
    )

    test_time = now()

    # ------------------------------------------
    # Record most recent test result
    # ------------------------------------------

    lifecycle["test_result"] = (
        "PASS"
        if passed
        else "FAIL"
    )

    lifecycle["last_test_at"] = test_time

    # ------------------------------------------
    # Firmware observed during test
    # ------------------------------------------

    firmware = data.get(
        "firmware"
    )

    if firmware:
        lifecycle["test_firmware"] = str(
            firmware
        )

    # ------------------------------------------
    # Successful test promotes node to TESTED
    # ------------------------------------------

    if passed:

        lifecycle["status"] = "TESTED"
        lifecycle["tested_at"] = test_time

    # ------------------------------------------
    # Failed test must NOT promote node
    # ------------------------------------------

    registry["updated_at"] = test_time

    save_registry(registry)

    return jsonify({
        "success": True,
        "node_id": node_id,
        "test_result": lifecycle["test_result"],
        "lifecycle_status": lifecycle.get(
            "status",
            "REGISTERED"
        )
    })



        # ------------------------------------------
        # SITE
        # ------------------------------------------

        site = node.setdefault(
            "site",
            {}
        )

        site["organization"] = request.form.get(
            "organization",
            ""
        ).strip()

        site["name"] = request.form.get(
            "site_name",
            ""
        ).strip()

        address = site.setdefault(
            "address",
            {}
        )

        address["street"] = request.form.get(
            "street",
            ""
        ).strip()

        address["city"] = request.form.get(
            "city",
            ""
        ).strip()

        address["state"] = request.form.get(
            "state",
            ""
        ).strip()

        address["postal_code"] = request.form.get(
            "postal_code",
            ""
        ).strip()

        latitude = request.form.get(
            "latitude",
            ""
        ).strip()

        longitude = request.form.get(
            "longitude",
            ""
        ).strip()

        elevation = request.form.get(
            "elevation",
            ""
        ).strip()

        site["latitude"] = (
            float(latitude)
            if latitude
            else None
        )

        site["longitude"] = (
            float(longitude)
            if longitude
            else None
        )

        site["elevation"] = (
            float(elevation)
            if elevation
            else None
        )

        site["location_description"] = request.form.get(
            "location_description",
            ""
        ).strip()

        # ------------------------------------------
        # OWNERSHIP / FUNDING
        # ------------------------------------------

        ownership = node.setdefault(
            "ownership",
            {}
        )

        ownership["device_owner"] = request.form.get(
            "device_owner",
            ""
        ).strip()

        ownership["funding_source"] = request.form.get(
            "funding_source",
            ""
        ).strip()

        ownership["project"] = request.form.get(
            "project",
            ""
        ).strip()

        ownership["award_id"] = request.form.get(
            "award_id",
            ""
        ).strip()

        # ------------------------------------------
        # CONTACTS
        # ------------------------------------------

        contacts = node.setdefault(
            "contacts",
            {}
        )

        primary = contacts.setdefault(
            "primary",
            {}
        )

        primary["name"] = request.form.get(
            "primary_name",
            ""
        ).strip()

        primary["organization"] = request.form.get(
            "primary_organization",
            ""
        ).strip()

        primary["email"] = request.form.get(
            "primary_email",
            ""
        ).strip()

        primary["phone"] = request.form.get(
            "primary_phone",
            ""
        ).strip()

        technical = contacts.setdefault(
            "technical",
            {}
        )

        technical["name"] = request.form.get(
            "technical_name",
            ""
        ).strip()

        technical["organization"] = request.form.get(
            "technical_organization",
            ""
        ).strip()

        technical["email"] = request.form.get(
            "technical_email",
            ""
        ).strip()

        technical["phone"] = request.form.get(
            "technical_phone",
            ""
        ).strip()

        # ------------------------------------------
        # DEPLOYMENT
        # ------------------------------------------

        deployment = node.setdefault(
            "deployment",
            {}
        )

        deployment["status"] = request.form.get(
            "deployment_status",
            "PLANNED"
        )

        deployment["planned_date"] = (
            request.form.get(
                "planned_date",
                ""
            ).strip()
            or None
        )

        deployment["deployed_at"] = (
            request.form.get(
                "deployed_at",
                ""
            ).strip()
            or None
        )

        deployment["installer"] = request.form.get(
            "installer",
            ""
        ).strip()

        deployment["installation_description"] = request.form.get(
            "installation_description",
            ""
        ).strip()

        deployment["notes"] = request.form.get(
            "notes",
            ""
        ).strip()

        # ------------------------------------------
        # LIFECYCLE
        # ------------------------------------------

        lifecycle = node.setdefault(
            "lifecycle",
            {}
        )

        if not lifecycle.get("registered_at"):
            lifecycle["registered_at"] = now()

        lifecycle["status"] = request.form.get(
            "lifecycle_status",
            lifecycle.get(
                "status",
                "REGISTERED"
            )
        )

        # ------------------------------------------
        # REGISTRY TIMESTAMP
        # ------------------------------------------

        registry["updated_at"] = now()

        save_registry(registry)

        return redirect(
            url_for(
                "register",
                node_id=node_id,
                saved="1"
            )
        )

    saved = request.args.get("saved") == "1"

    return render_template(
        "registration.html",
        node=node,
        node_id=node_id,
        saved=saved
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    print(
        f"Starting UCM registration application"
    )

    print(
        f"Registry: {REGISTRY_FILE}"
    )

    app.run(
        host=HOST,
        port=PORT,
        debug=False
    )
