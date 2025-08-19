import json

def get_web_features():
    # Use data.extended.json to get compat_features for all features.
    with open("data.extended.json") as f:
        data_extended = json.load(f)
    features = data_extended["features"]
    keep_keys = ['name', 'description', 'compat_features']
    for data in features.values():
        for key in list(data.keys()):
            if key not in keep_keys:
                del data[key]
    return features
