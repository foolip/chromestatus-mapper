import httpx
import json


# Yield all entries from chromestatus.com. Because the newest entry is returned
# first and entries might be created while we're iterating, it's possible that
# the same entry is yielded multiple times. If this is a problem they have to be
# deduplicated by ID by the client.
async def get_chromestatus_entries():
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
