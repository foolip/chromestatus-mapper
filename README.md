# chromestatus to web-features mapper

This project uses a generative AI model to map web platform features from [chromestatus.com](https://chromestatus.com) to [web-features](https://github.com/web-platform-dx/web-features).

The approach is to include all features from web-features as well as the chromestatus entries in the prompt, with instructions to identify the feature each entry is most likely referring to, if any. The output is JSON which is then parsed to get the results. Many entries are processed in each prompt for efficiency.

## Requirements

- Python 3.9+
- [uv](https://docs.astral.sh/uv/)
- An environment variable `GEMINI_API_KEY` with a valid API key
- `chromestatus.json`: A JSON export of features from chromestatus.com
- `data.extended.json`: The web-features data set

## Running

```bash
uv sync
uv run main.py
```
