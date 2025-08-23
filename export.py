import json
import csv

from review import MAPPING_REVIEW_FILE

MAPPING_EXPORT_FILE = 'mapping-export.csv'

def main():
    with open(MAPPING_REVIEW_FILE) as f:
        data = json.load(f)

    rows = []

    # Sort by web-features ID to allow for a final skimming review in the
    # chromestatus.com import tool.
    data.sort(key=lambda x: x["web_features_id"])

    for item in data:
        if item['review_status'] == 'accept':
            rows.append({
                'Chrome Status Entry': item['chromestatus_id'],
                'Feature ID': item['web_features_id'],
            })

    if rows:
        with open(MAPPING_EXPORT_FILE, 'w') as csvfile:
            fieldnames = ['Chrome Status Entry', 'Feature ID']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {MAPPING_EXPORT_FILE} with {len(rows)} rows")


if __name__ == "__main__":
    main()
