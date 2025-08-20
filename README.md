# chromestatus to web-features mapper

This project uses a generative AI model to map web platform features from [chromestatus.com](https://chromestatus.com) to [web-features](https://github.com/web-platform-dx/web-features).

The approach is to include all features from web-features as well as the chromestatus entries in the prompt, with instructions to identify the feature each entry is most likely referring to, if any. The output is JSON which is then parsed to get the results. Many entries are processed in each prompt for efficiency.

## Requirements

- Python 3.9+
- [uv](https://docs.astral.sh/uv/)
- An environment variable `GEMINI_API_KEY` with a valid API key

## Running

First update the `chromestatus.json` and `web-features.json` files:

```bash
uv run update.py
```

Then run the main classification script:

```bash
uv run main.py
```

To review the mappings through a web app:

```bash
uv run review.py
```

Finally, to export the accepted mappings to a CSV file:

```bash
uv run export.py
```
