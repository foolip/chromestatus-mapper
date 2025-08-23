import json
import csv

from update import CHROMESTATUS_FILE, WEB_FEATURES_FILE
from review import MAPPING_REVIEW_FILE

MAPPING_EXPORT_FILE = "mapping-export.csv"

with open(CHROMESTATUS_FILE) as f:
    CHROMESTATUS = json.load(f)

CHROMESTATUS_BY_ID = {str(entry["id"]): entry for entry in CHROMESTATUS}

with open(WEB_FEATURES_FILE) as f:
    WEB_FEATURES = json.load(f)


def main():
    with open(MAPPING_REVIEW_FILE) as f:
        data = json.load(f)

    rows = []

    # Sort by web-features ID to allow for a final skimming review in the
    # chromestatus.com import tool.
    data.sort(key=lambda x: x["web_features_id"])

    for item in data:
        # Skip invalid IDs and no-op changes.
        entry = CHROMESTATUS_BY_ID.get(str(item["chromestatus_id"]))
        if not entry:
            continue
        id = item["web_features_id"]
        if id not in WEB_FEATURES["features"]:
            continue
        if entry["web_feature"] == id:
            continue

        # Export accepted mappings.
        if item["review_status"] == "accept":
            rows.append(
                {
                    "Chrome Status Entry": item["chromestatus_id"],
                    "Feature ID": item["web_features_id"],
                }
            )

    if rows:
        with open(MAPPING_EXPORT_FILE, "w") as csvfile:
            fieldnames = ["Chrome Status Entry", "Feature ID"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {MAPPING_EXPORT_FILE} with {len(rows)} rows")


if __name__ == "__main__":
    main()
