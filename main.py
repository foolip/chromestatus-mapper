import asyncio
import httpx
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


# Yield all entries from chromestatus.com. Because the newest entry is returned
# first and entries might be created while we're iterating, it's possible that
# the same entry is yielded multiple times. If this is a problem they have to be
# deduplicated by ID by the client.
async def chromestatus_entries():
    num = 500
    start = 0
    async with httpx.AsyncClient() as client:
        while True:
            url = f"https://chromestatus.com/api/v0/features?start={start}&num={num}"
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            if not resp.text.startswith(")]}'\n"):
                raise Exception(
                    "Expected API response did not begin with the magic sequence."
                )
            data = json.loads(resp.text[5:])
            features = data.get("features")
            # Iteration is done when the API returns no features. This does mean that
            # we make one more request than necessary, but it's simple and works.
            if not features:
                break
            keep_keys = ["id", "name", "summary"]
            for entry in features:
                for key in list(entry.keys()):
                    if key not in keep_keys:
                        del entry[key]
                yield entry
            start += num


web_features_example = {
    "abbr": {
        "name": "<abbr>",
        "description": "The `<abbr>` HTML element represents an abbreviation or acronym.",
        "spec": "https://html.spec.whatwg.org/#the-abbr-element",
        "compat_features": ["html.elements.abbr"],
    },
    "aborting": {
        "name": "AbortController and AbortSignal",
        "description": "The `AbortController` and `AbortSignal` APIs allow you to cancel an ongoing operation, such as a `fetch()` request.",
        "spec": "https://dom.spec.whatwg.org/#aborting-ongoing-activities",
        "compat_features": [
            "api.AbortController.AbortController",
            "api.AbortController.signal",
        ],
    },
    "anchor-positioning": {
        "name": "Anchor positioning",
        "description": "Anchor positioning places an element based on the position of another element.",
        "spec": "https://drafts.csswg.org/css-anchor-position/",
        "compat_features": [
            "api.CSSPositionTryRule",
            "css.at-rules.position-try",
            "css.properties.anchor-name",
            "css.properties.position-anchor",
        ],
    },
}

input_example = {
    "1234": {
        "name": "Abbreviator API",
        "summary": "Shipping an API to compute common abbreviations for words. Developer feedback is good.",
    },
    "1337": {
        "name": "@position-try inside mixins",
        "summary": "Support @position-try in mixins. Previously this was dropped at parse time.",
    },
    "1984": {
        "name": "Deprecate controller.signal",
        "summary": "controller.signal is no longer recommended, use cancelable promises instead",
    },
}

output_example = {
    "1234": {
        "id": "NOT_FOUND",
        "confidence": 0,
        "notes": "Not part of web-features. Not related to `<abbr>` which is about displaying abbreviations, not computing them.",
    },
    "1337": {
        "id": "anchor-positioning",
        "confidence": 70,
        "notes": "A change to the `@position-try` which is in the `compat_features` of this feature, but could perhaps be considered part of CSS mixins",
    },
    "1984": {
        "id": "aborting",
        "confidence": 90,
        "notes": "`controller.signal` refers to `AbortController`'s `signal` property which is part of aborting.",
    },
}

system_prompt = f"""
Your role is an expert on the web platform and its features, from the point of view of a web developer.

Your task is to act as a classification engine for web platform features.

You will be classifying user input against the web-features data set, which will be provided in the prompt as a JSON object on this form:

```json
{json.dumps(web_features_example, indent=2)}
```

The `name` and `description` fields are the most important to understanding what a feature is. The `spec` URL can be useful if the same link appears in the user input, but it's not a strong signal. The `compat_features` array is a list of identifiers for the feature's API surface, following a number of conventions. For example "html.elements.a" refers to the HTML element `<a>`. Use the `compat_features` array to get a crisper understanding of what is in scope and out of scope for each feature.

The input will be a JSON object where the keys are unique identifiers and the values are objects with key-value information about the feature being sought. Example input:

```json
{json.dumps(input_example, indent=2)}
```

There may be other keys than those that appear in this example, use them as you see fit.

The output must be a JSON object using the input keys, and values are objects with `id`, `confidence`, and `notes` fields:
- `id` (string) is the web-features identifier, one of the top-level keys from the web-features data set.
- `confidence` (number) is your confidence in the classification as a integer percentage. Treat it as the probability that the classification is correct. Only use multiples of 10.
- `notes` (string) is one or two sentences to help a reviewer focus on what's important. Say why you are certain or uncertain.

Example output:

```json
{json.dumps(output_example, indent=2)}
```

Rules for classifying the each feature (one of the nested objects in the overall input):
1. Use the web-features data and your knowledge of the web platform to identify the feature the user is most likely referring to.
2. If there is no plausible match, use the special `id` "NOT_FOUND".
3. If there is a match, the `id` MUST be the web-features identifier. The identifiers are the top-level keys in the web-features data set. No other strings or values are permissible. Additionally provide `confidence` and `notes` as described above.

Rules for formatting the response:
1. Your response MUST be a single JSON object.
2. The keys MUST be the same as in the input object.
3. Each value MUST be an object with keys `id`, `confidence`, and `notes`. All are required, unless `id` is the special value "NOT_FOUND".
4. The output MUST be valid JSON.
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


async def main():
    config = types.GenerateContentConfig(system_instruction=system_prompt)

    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client()

    # Load existing mapping from disk to support resuming
    try:
        with open("mapping.json") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        mapping = {}

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

    async for entry in chromestatus_entries():
        id = str(entry["id"])
        del entry["id"]
        if id in mapping:
            # print(f'Entry {id} already mapped')
            continue
        input[id] = entry
        process()
    process(end=True)


if __name__ == "__main__":
    asyncio.run(main())
