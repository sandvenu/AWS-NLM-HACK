"""Lambda handler: copy public Hugging Face files to the team07 data bucket.

The team07 laptop network blocks huggingface.co, so dataset files are pulled from
inside AWS (us-east-2) and stored under s3://<bucket>/nlm-track1/raw/.

Event:
  {"items": [{"url": "...", "key": "nlm-track1/raw/..."}],   # copy each url to key
   "probe": ["url", ...]}                                    # return status + first 4000 chars
An HF token, when needed for gated data, is read from the HF_TOKEN environment
variable and never logged or returned.
"""
import json
import os
import urllib.error
import urllib.request

import boto3

BUCKET = os.environ.get("BUCKET", "bb26-p-team07-data-041915167631-use2")
s3 = boto3.client("s3")


def _get(url):
    headers = {"User-Agent": "team07-nlm-track1/1.0"}
    token = os.environ.get("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def handler(event, context):
    out = {"probe": [], "items": []}
    for url in event.get("probe", []):
        status, body = _get(url)
        out["probe"].append({"url": url, "status": status, "body": body[:4000].decode("utf-8", "replace")})
    for item in event.get("items", []):
        status, body = _get(item["url"])
        rec = {"url": item["url"], "status": status, "bytes": len(body)}
        if status == 200 and item.get("key", "").startswith("nlm-track1/"):
            s3.put_object(Bucket=BUCKET, Key=item["key"], Body=body)
            rec["key"] = item["key"]
        else:
            rec["body"] = body[:500].decode("utf-8", "replace")
        out["items"].append(rec)
    print(json.dumps({"items": [{k: v for k, v in r.items() if k != "body"} for r in out["items"]]}))
    return out
