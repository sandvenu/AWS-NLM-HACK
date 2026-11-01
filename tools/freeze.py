"""Record SHA-256 hashes of the frozen test sets in testsets/MANIFEST.json.

Run once when a test set is created, then commit. Refuses to change the hash of a file
already in the manifest (a frozen set never changes).

  python tools/freeze.py testsets/execution_telemath_synth.jsonl --source "..." --licence "..."
"""
import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from nlm.common import read_jsonl, sha256_file  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--unit", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--licence", required=True)
    ap.add_argument("--build", required=True, help="command that rebuilds the file")
    a = ap.parse_args()
    mpath = os.path.join(ROOT, "testsets", "MANIFEST.json")
    manifest = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {"files": {}}
    rel = os.path.relpath(os.path.abspath(a.path), ROOT).replace("\\", "/")
    sha = sha256_file(os.path.join(ROOT, rel))
    if rel in manifest["files"] and manifest["files"][rel]["sha256"] != sha:
        raise SystemExit(f"{rel} is frozen with sha256 {manifest['files'][rel]['sha256']}; refusing to change it")
    manifest["files"][rel] = {"unit": a.unit, "sha256": sha, "items": len(read_jsonl(os.path.join(ROOT, rel))),
                              "source": a.source, "licence": a.licence, "build": a.build,
                              "frozen_at": manifest["files"].get(rel, {}).get("frozen_at")
                              or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    with open(mpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(json.dumps(manifest["files"][rel], indent=2))


if __name__ == "__main__":
    main()
