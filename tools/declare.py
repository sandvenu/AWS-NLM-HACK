"""Write evidence/declared/<run_id>.json locally and to S3 BEFORE a run starts.

Refuses to overwrite an existing declaration (locally or in S3), so a target cannot be
changed after results are seen.

  python tools/declare.py --run-id 2026-11-02T06-00-knowledge-base-01 --unit knowledge \
      --metric exact_match --value 0.45 --test-file testsets/knowledge_teleqna.jsonl \
      --model-id otel-llm-1.7b-it@2a2d417b --adapter-id none --note "baseline"
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess

import boto3

BUCKET = "bb26-p-team07-data-041915167631-use2"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--metric", required=True)
    ap.add_argument("--value", type=float, required=True)
    ap.add_argument("--direction", default=">=", choices=[">=", "<="])
    ap.add_argument("--test-file", default="")
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--adapter-id", default="none")
    ap.add_argument("--grader", default="rule-based-parser-v1")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    path = os.path.join(ROOT, "evidence", "declared", f"{a.run_id}.json")
    key = f"evidence/declared/{a.run_id}.json"
    s3 = boto3.client("s3", region_name="us-east-2")
    if os.path.exists(path):
        raise SystemExit(f"{path} already exists; declarations are write-once")
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        raise SystemExit(f"s3://{BUCKET}/{key} already exists; declarations are write-once")
    except s3.exceptions.ClientError:
        pass
    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    decl = {
        "run_id": a.run_id,
        "team_code": "team07",
        "unit": a.unit,
        "target": {"metric": a.metric, "value": a.value, "direction": a.direction},
        "test_set": os.path.relpath(os.path.join(ROOT, a.test_file), ROOT).replace("\\", "/") if a.test_file else None,
        "test_set_sha256": sha256_file(os.path.join(ROOT, a.test_file)) if a.test_file else None,
        "model_id": a.model_id,
        "adapter_id": a.adapter_id,
        "grader": a.grader,
        "git_commit": commit,
        "declared_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "note": a.note,
    }
    body = json.dumps(decl, indent=2) + "\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    s3.put_object(Bucket=BUCKET, Key=key, Body=body.encode())
    print(body)


if __name__ == "__main__":
    main()
