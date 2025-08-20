import json
import os
import asyncio
from flask import Flask, jsonify, request, send_from_directory

from update import CHROMESTATUS_FILE, WEB_FEATURES_FILE

app = Flask(__name__)

from main import MAPPING_TENTATIVE_FILE

MAPPING_REVIEW_FILE = "mapping-review.json"

with open(CHROMESTATUS_FILE) as f:
    CHROMESTATUS = json.load(f)

CHROMESTATUS_BY_ID = {str(entry["id"]): entry for entry in CHROMESTATUS}

with open(WEB_FEATURES_FILE) as f:
    WEB_FEATURES = json.load(f)

_queue = None


def load_queue() -> list[dict]:
    """Loads or created the review queue. This includes reviewed and pending mappings."""

    # Use the existing file if it's there to support resuming.
    try:
        with open(MAPPING_REVIEW_FILE) as f:
            queue = json.load(f)
            print(f"Using existing {MAPPING_REVIEW_FILE} with {len(queue)} entries")
            return queue
    except FileNotFoundError:
        pass

    # Create a new filtered/sorted review queue from the tentative mappings.
    queue = []

    with open(MAPPING_TENTATIVE_FILE) as f:
        tentative = json.load(f)

    for id, outcome in tentative.items():
        assert isinstance(id, str)
        assert isinstance(outcome, dict)
        assert "result" in outcome or "failure" in outcome

        # Skip failure objects.
        if "failure" in outcome:
            continue

        # Ensure the chromestatus entry really exists.
        entry = CHROMESTATUS_BY_ID.get(id)
        if not entry:
            continue

        # Skip anything already mapped to a valid web-features ID.
        existing_feature = entry["web_feature"]
        if existing_feature in WEB_FEATURES["features"]:
            continue

        # Drop results with invalid web-features IDs.
        feature = outcome["result"]
        if feature not in WEB_FEATURES["features"]:
            continue

        # Put the ID on the object itself to be self-contained.
        queue.append(
            {
                "chromestatus_id": id,
                "web_features_id": feature,
                "confidence": outcome["confidence"],
                "notes": outcome.get("notes", ""),
                "review_status": "pending",
            }
        )

    # Sort by queue by chromestatus update date, most recent first.
    queue.sort(
        key=lambda x: CHROMESTATUS_BY_ID[x["chromestatus_id"]]["updated"]["when"],
        reverse=True,
    )

    return queue


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)


@app.route("/api/queue")
def get_queue():
    return jsonify(_queue)


@app.route("/api/save", methods=["POST"])
def save_review():
    data = request.get_json()
    if (
        not data
        or "chromestatus_id" not in data
        or "web_features_id" not in data
        or "review_status" not in data
    ):
        return jsonify({"error": "Invalid data"}), 400

    found = False
    for item in _queue:
        if (
            item["chromestatus_id"] == data["chromestatus_id"]
            and item["web_features_id"] == data["web_features_id"]
        ):
            item["review_status"] = data["review_status"]
            found = True
            break

    if not found:
        return jsonify({"error": "Item not found in review queue"}), 400

    # Write whole review queue to disk. Yes, on every incremental update, in
    # order to support resuming from any point.
    with open(MAPPING_REVIEW_FILE, "w") as f:
        json.dump(_queue, f, indent=2)

    return jsonify({"success": True})


@app.route("/api/chromestatus/<id>")
def chromestatus_data(id: str):
    """Returns chromestatus data for a single entry."""
    entry = CHROMESTATUS_BY_ID.get(id)
    if entry:
        return jsonify(entry)
    return jsonify({"error": f"Entry not found: {id}"}), 404


@app.route("/api/web-features/<id>")
def web_feature_data(id: str):
    """Returns web-features data for a single feature."""
    feature = WEB_FEATURES["features"].get(id)
    if feature:
        return jsonify(feature)
    return jsonify({"error": f"Feature not found: {id}"}), 404


if __name__ == "__main__":
    _queue = load_queue()
    app.run(debug=True, port=5001)
