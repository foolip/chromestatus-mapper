import json
import csv

from review import MAPPING_REVIEW_FILE

MAPPING_EXPORT_FILE = 'mapping-export.csv'

def main():
    with open(MAPPING_REVIEW_FILE) as f:
        data = json.load(f)

    rows = []

    for item in data:
        if item['review_status'] == 'accept':
            rows.append({
                'id': item['chromestatus_id'],
                'web_feature': item['web_features_id'],
            })

    if rows:
        with open(MAPPING_EXPORT_FILE, 'w') as csvfile:
            fieldnames = ['id', 'web_feature']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {MAPPING_EXPORT_FILE} with {len(rows)} rows")

if __name__ == "__main__":
    main()
