import json
import csv
import sys

from web_features import get_web_features

def export(json_file_path):
    """
    Reads the mapping JSON file, separates the data into success and failure
    objects, and writes them to two separate CSV files.
    """

    features = set(get_web_features().keys())
    assert 'xhr' in features # sanity check

    with open(json_file_path) as f:
        data = json.load(f)

    # Categorize outcomes into successes and failures
    successes = []
    failures = []
    for entry_id, outcome in data.items():
        match outcome:
            case {'failure': _}:
                failures.append({
                    'entry': entry_id,
                    'notes': outcome.get('notes', '')
                })
            case {'result': _}:
                feature_id = outcome['result']
                if feature_id in features:
                    successes.append({
                        'entry': entry_id,
                        'feature': feature_id,
                        'confidence': outcome.get('confidence', 0),
                        'notes': outcome.get('notes', '')
                    })
                else:
                    print(f"Warning: treating a mapping for {entry_id} to {feature_id} as a failure (invalid ID)")
                    failures.append({
                        'entry': entry_id,
                        'notes': f'Mapped to invalid feature ID: {feature_id}'
                    })
            case _:
                print(f"Warning: skipping a mapping that was neither a success nor a failure: {id}")

    # Write successes to CSV
    success_csv_path = 'successes.csv'
    if successes:
        with open(success_csv_path, 'w') as csvfile:
            fieldnames = ['entry', 'feature', 'confidence', 'notes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(successes)
        print(f"Successfully created {success_csv_path} with {len(successes)} entries.")

    # Write failures to CSV
    failure_csv_path = 'failures.csv'
    if failures:
        with open(failure_csv_path, 'w') as csvfile:
            fieldnames = ['entry', 'notes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failures)
        print(f"Successfully created {failure_csv_path} with {len(failures)} entries.")

if __name__ == "__main__":
    json_file_path = sys.argv[1] if len(sys.argv) > 1 else 'mapping-updated.json'
    export(json_file_path)
