import asyncio
import httpx
import json

CHROMESTATUS_FILE = "chromestatus.json"
WEB_FEATURES_FILE = "web-features.json"


async def update_chromestatus() -> None:
    entries = []

    # Because the newest entry is returned first and entries might be created
    # while we're iterating, it's possible that the same entry is seen multiple
    # times. Keep track of seen IDs to skip them.
    seen_ids: set[int] = set()

    num = 500
    start = 0
    async with httpx.AsyncClient() as client:
        while True:
            print(f"Fetching chromestatus entries {start + 1}-{start + num}")
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
            for entry in features:
                if entry["id"] in seen_ids:
                    continue
                seen_ids.add(entry["id"])
                entries.append(entry)
            start += num

    entries.sort(key=lambda e: e["id"])

    with open(CHROMESTATUS_FILE, "w") as f:
        json.dump(entries, f, indent=2)

    print(f"Wrote {len(entries)} entries to {CHROMESTATUS_FILE}")


async def update_web_features() -> None:
    latest_release_url = (
        "https://api.github.com/repos/web-platform-dx/web-features/releases/latest"
    )

    asset_name = "data.json"

    async with httpx.AsyncClient() as client:
        print(f"Fetching latest web-features release")
        response = await client.get(latest_release_url)
        response.raise_for_status()
        release_data = response.json()

        tag_name = release_data["tag_name"]
        assets = release_data["assets"]

        asset_url = None
        for asset in assets:
            if asset["name"] == asset_name:
                asset_url = asset["browser_download_url"]
                break

        if not asset_url:
            raise Exception(f"No {asset_name} asset for web-features {tag_name}")

        print(f"Fetching {asset_name} for web-features {tag_name}")
        asset_response = await client.get(asset_url, follow_redirects=True)
        asset_response.raise_for_status()

        # Parse and reserialize to ensur it's JSON and to get indent=2
        data = json.loads(asset_response.content)

        with open(WEB_FEATURES_FILE, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Wrote {len(data['features'].keys())} features to {WEB_FEATURES_FILE}")


async def update() -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(update_chromestatus())
        tg.create_task(update_web_features())


if __name__ == "__main__":
    asyncio.run(update())
