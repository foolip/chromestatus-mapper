import json

from google import genai
from google.genai import types


def web_features_data():
    # Use data.extended.json to get compat_features for all features.
    with open("data.extended.json") as f:
        data_extended = json.load(f)
    features = data_extended["features"]
    # keep_keys = ['name', 'description', 'spec', 'compat_features']
    keep_keys = ["name", "description"]
    for data in features.values():
        for key in list(data.keys()):
            if key not in keep_keys:
                del data[key]
    return features


def chromestatus_data():
    with open("chromestatus.json") as f:
        entries = json.load(f)
    keep_keys = ["id", "name", "summary"]
    for data in entries:
        for key in list(data.keys()):
            if key not in keep_keys:
                del data[key]
    return entries


input_example = {
    "1001": {
        "name": "requestIdleCallback()",
        "summary": "an API to cooperatively schedule background tasks",
        "spec": "https://w3c.github.io/requestidlecallback/",
    },
    "1002": {"description": "a CSS feature to make rounded corners on boxes"},
}

web_features_example = {
    "a": {
        "name": "<a>",
        "description": "The <a> element creates a link.",
        "spec": "https://html.spec.whatwg.org/#the-a-element",
        "compat_features": ["api.HTMLAnchorElement", "html.elements.a"],
    }
}

system_prompt = f"""
Your task is to act as a classification engine for web platform features.

Your input will be a JSON object where the keys are unique identifiers and the values are objects with key-value information about the feature being sought. Example input:
```json
{json.dumps(input_example, indent=2)}
```

This is just an example, there may be other keys than those that appear above.

You will be classifying user input against the web-features data set, which will be provided in the prompt as a JSON object.

The web-features data set will be on this form:
```json
{json.dumps(web_features_example, indent=2)}
```

The `name` and `description` fields are the most important to understanding what a feature is. The `spec` URL can be useful if the same link appears in the user input, but it's not a strong signal. The `compat_features` array is a list of identifiers for the feature's API surface, following a number of conventions. For example "html.elements.a" refers to the HTML element `<a>`. Use the `compat_features` array to get a crisper understanding of what is in scope and out of scope for each feature.

Rules for identifying a web platform feature based on an input object:
1. Use the web-features data and your knowledge of the web platform to identify the feature the user is most likely referring to.
2. If there is no plausible match, use the special value "NOT_FOUND".
3. If there is a match, the result MUST be the web-features identifier. The identifiers are the top-level keys in the web-features data set. No other strings or values are permissible.

Rules for formatting the response:
1. Your response MUST be a single JSON object.
2. The keys MUST be the same as in the input object.
3. Each value MUST be a string representing the name of the identified feature.
3. The output MUST be valid JSON that can be parsed directly.
4. DO NOT wrap the JSON  in ```json (triple backticks) or any other markup.
"""


def make_prompt(candidates, user_input):
    return f"""The web-features data set:
```json
{json.dumps(candidates, indent=2)}
```

User input to classify:
```json
{json.dumps(user_input, indent=2)}
```
"""


def extract_json_object(text):
    start_index = text.find("{")
    end_index = text.rfind("}")
    if start_index != -1 and end_index > start_index:
        json_string = text[start_index : end_index + 1]
        return json.loads(json_string)
    return {}


def main():
    config = types.GenerateContentConfig(system_instruction=system_prompt)

    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client()

    # Load existing mapping from disk to support resuming
    try:
        with open("mapping.json") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        mapping = {}

    entries = chromestatus_data()
    candidates = web_features_data()

    # below code will add entries to input and call process(),
    # with flush=True the last time.
    max_entries = 250
    input = {}

    def process(end=False):
        count = len(input)
        if count == 0:
            return
        if count < max_entries and not end:
            return

        print(f"Processing {count} entries", flush=True)

        prompt = make_prompt(candidates, input)
        input.clear()

        response = client.models.generate_content(
            model="gemini-2.5-pro", contents=prompt, config=config
        )

        result = extract_json_object(response.text)
        if not result:
            print("No JSON object found in results")
            return

        print(f"Got {len(result)} results, saving")
        mapping.update(result)
        with open("mapping-updated.json", "w") as f:
            json.dump(mapping, f, indent=2, sort_keys=True)

    for entry in entries:
        id = str(entry["id"])
        del entry["id"]
        if id in mapping:
            # print(f'Entry {id} already mapped')
            continue
        input[id] = entry
        process()
    process(end=True)


if __name__ == "__main__":
    main()
