import asyncio
import json

from google import genai
from google.genai import types

from update import CHROMESTATUS_FILE, WEB_FEATURES_FILE

web_features_example = {
    "abbr": {
        "name": "<abbr>",
        "description": "The `<abbr>` HTML element represents an abbreviation or acronym.",
        "compat_features": ["html.elements.abbr"],
    },
    "aborting": {
        "name": "AbortController and AbortSignal",
        "description": "The `AbortController` and `AbortSignal` APIs allow you to cancel an ongoing operation, such as a `fetch()` request.",
        "compat_features": [
            "api.AbortController.AbortController",
            "api.AbortController.signal",
        ],
    },
    "anchor-positioning": {
        "name": "Anchor positioning",
        "description": "Anchor positioning places an element based on the position of another element.",
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
        "title": "Abbreviator API",
        "summary": "Requesting to ship this API to compute common abbreviations for words. Developer feedback was good.",
    },
    "1337": {
        "title": "@position-try inside mixins",
        "summary": "Support @position-try in mixins. Previously this was dropped at parse time.",
    },
    "1984": {
        "title": "Deprecate controller.signal",
        "summary": "controller.signal is no longer recommended, use cancelable promises instead",
    },
}

output_example = {
    "1234": {
        "failure": True,
        "notes": "Not related to `<abbr>` which is for marking up abbreviations, not an API for computing them.",
    },
    "1337": {
        "result": "anchor-positioning",
        "confidence": 70,
        "notes": "A change to the `@position-try` which is part anchor positioning, but could perhaps be considered part of mixins",
    },
    "1984": {
        "result": "aborting",
        "confidence": 90,
        "notes": "`controller.signal` refers to `AbortController`'s `signal` property which is part of aborting.",
    },
}

system_prompt = f"""
## Persona

You are an expert on the web platform, with deep knowledge from the perspectives of both web developers and browser engineers. You understand the nuances of developer-facing technical writing (like in `web-features`) and implementation-specific process (like in `chromestatus`).

---

## Objective

Your task is to classify input `chromestatus` entries against a provided `web-features` dataset. You will process a batch of entries and return a single JSON object with the classification for each.

---

## Context and data formats

### The `web-features` dataset

This is your reference dataset, with over 1000 features described from a web developer's point of view. It is provided as a single JSON object.

- **Keys**: Unique web-feature identifiers.
- **Values**: An object with the following properties:
  - `name`: A short name of the feature.
  - `description`: A developer-focused explanation.
  - `compat_features`: An array of dot-separated strings ("paths" from browser-compat-data) representing the specific API surface of the feature.

### Input: `chromestatus` entries

You will receive multiple `chromestatus` entries to be classified, provided as a single JSON object:

- **Keys**: Opaque identifiers with no meaning, their only purpose is to link the output results back to the input entries.
- **Values**: An object with the following properties:
  - `title`: A title in terms of what's changing in Chrome.
  - `summary`: A description of the change from a browser engineer's perspective, including the risks of making the change.

-----

## Instructions

For each `chromestatus` entry in the input object, perform the following steps:

1. **Analyze**: Examine the `title` and `summary`. Identify key terms and concepts.
2. **Match**: Search the provided `web-features` dataset for the most relevant feature.
   - Look for matches between the key terms and concepts and each feature's `name`, `description`, and `compat_features`.
   - Use your expert knowledge to bridge terminology gaps.
3. **Decide and construct**:
   - If you find one or more plausible matches, select the **single best** match. Construct a **success object**. Use the `confidence` and `notes` fields to express any ambiguity.
   - If you find no plausible matches, construct a **failure object**. If a candidate match turned out to be implausible on closer analysis, use `notes` to explain why.

-----

## Output format and rules

### Success objects

Used when one or more matches were found. The object has three required keys:

- `result` (string): The matching identifier (key) from the `web-features` dataset.
- `confidence` (number): Your confidence in the match as an integer percentage from 0 to 100. Must be a multiple of 10.
  - **90-100**: High confidence, direct match via unambiguous technical terms, syntax, or concepts.
  - **60-80**: Medium confidence, with ambiguity in the match.
  - **10-50**: Low confidence, a speculative match.
- `notes` (string): A concise (1-2 sentences) explanation of your reasoning. Mention the specific terms that led to the best match and explain any uncertainty.

### Failure objects

Used when no matching feature was found. The object has two required keys:

- `failure` (boolean): Must be `true`.
- `notes` (string): A concise (1-2 sentences) explanation for why a seeming match turned out to be implausible, or the empty string.

### Output format

The output object must use the exact same keys as the input object, and the values must be either a success or failure object.

Your entire response must be the output object as JSON. Do not include any text before or after the JSON.

-----

## Example

Here is an complete end-to-end example of the inputs and outputs.

Example `web-features` dataset with only {len(web_features_example)} features:

```json
{json.dumps(web_features_example, indent=2)}
```

Example input object with {len(input_example)} `chromestatus` entries:

```json
{json.dumps(input_example, indent=2)}
```

Given this `web-features` dataset and these `chromestatus` entries, the expected output object is:

```json
{json.dumps(output_example, indent=2)}
```
"""


def make_prompt(candidates, user_input):
    return f"""The `web-features` dataset:

```json
{json.dumps(candidates, indent=2)}
```

The input `chromestatus` entries to classify:

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

    # Load chromestatus and web-features data from disk (created by update.py)
    with open(CHROMESTATUS_FILE) as f:
        chromestatus = json.load(f)

    with open(WEB_FEATURES_FILE) as f:
        web_features = json.load(f)
    candidates = {}
    for id, data in web_features["features"].items():
        # Make a filtered object with the keys in order of importance.
        candidates[id] = {
            "name": data["name"],
            "description": data["description"],
            # Some features (like AVIF) don't have compat features.
            "compat_features": data.get("compat_features", []),
        }

    # below code will add entries to input and call process(),
    # with flush=True the last time.
    input = {}

    # max_entries was chosen based on measuring how long it takes per request,
    # and performance plateaus around this point.
    max_entries = 100

    async def process(end=False):
        count = len(input)
        if count == 0:
            return
        if count < max_entries and not end:
            return

        print(f"Processing {count} entries", flush=True)

        prompt = make_prompt(candidates, input)
        input.clear()

        response = await client.aio.models.generate_content(
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

    for entry in chromestatus:
        id = str(entry["id"])
        if id in mapping:
            # print(f'Entry {id} already mapped')
            continue

        # `name` is changed to `title` so that it cannot be conflated with the
        # `name` field in web-features. `summary` is just copied.
        input[id] = {"title": entry["name"], "summary": entry["summary"]}

        await process()

    await process(end=True)


if __name__ == "__main__":
    asyncio.run(main())
