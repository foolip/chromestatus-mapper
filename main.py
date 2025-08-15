import json

from google import genai
from google.genai import types

example = {
  "1001": {
    "name": "requestIdleCallback()",
    "abstract": "an API to cooperatively schedule background tasks",
    "spec": "https://w3c.github.io/requestidlecallback/"
  },
  "1002": {
    "description": "a CSS feature to make rounded corners on boxes"
  }
}

system_prompt = f"""
Your task is to act as a classification engine, making use of your extensive knowledge of the web platform.

Your input will be a JSON object where the keys are unique identifiers and the values are objects with key-value information about the feature being sought. Example input:
```json
{json.dumps(example, indent=2)}
```

This is just an example, there may be other keys than those that appear above.

Rules for identifying a web platform feature based on an input object:
1. Use your knowledge of the web platform to identify the feature that the input object is most likely referring to.
2. Return a string identifier like those used on caniuse.com, such as "abortcontroller".
3. If no feature can be identified, use the special value "NOT_FOUND".

Rules for formatting the response:
1. Your response MUST be a single JSON object.
2. The keys MUST be the same as in the input object.
3. Each value MUST be a string representing the name of the identified feature.
3. The output MUST be valid JSON that can be parsed directly.
4. DO NOT wrap the JSON ```json (triple backticks) or any other markup.
"""

config=types.GenerateContentConfig(
    system_instruction=system_prompt
)

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

prompt = f"""Input:
```json
{json.dumps(example, indent=2)}
```
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=config
)

print(response.text)
