"""Read-only live test: show one per-item record for a run id, its declaration, and the
matching CloudWatch log line written by the SageMaker job. Uses only S3 GetObject and
CloudWatch Logs reads (works after the account freeze).

  python tools/show_record.py --run-id <run_id> --item <item_id>
"""
import argparse
import json
import time

import boto3

REGION = "us-east-2"
BUCKET = "bb26-p-team07-data-041915167631-use2"
LOG_GROUP = "/aws/sagemaker/TrainingJobs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--item", required=True)
    a = ap.parse_args()
    s3 = boto3.client("s3", region_name=REGION)
    decl = json.loads(s3.get_object(Bucket=BUCKET, Key=f"evidence/declared/{a.run_id}.json")["Body"].read())
    print("DECLARATION", json.dumps(decl, indent=2))
    body = s3.get_object(Bucket=BUCKET, Key=f"evidence/records/{a.run_id}/records.jsonl")["Body"].read().decode()
    rec = next((json.loads(l) for l in body.splitlines() if l and json.loads(l)["item_id"] == a.item), None)
    if rec is None:
        raise SystemExit(f"item {a.item} not found in run {a.run_id}")
    print("RECORD", json.dumps(rec, indent=2, ensure_ascii=False))

    logs = boto3.client("logs", region_name=REGION)
    stream_prefix = None
    summary = json.loads(s3.get_object(Bucket=BUCKET, Key=f"evidence/records/{a.run_id}/summary.json")["Body"].read())
    stream_prefix = summary.get("training_job_name")
    resp = logs.filter_log_events(logGroupName=LOG_GROUP, logStreamNamePrefix=stream_prefix,
                                  filterPattern=f'"run_id={a.run_id}" "item={a.item} "')
    for ev in resp.get("events", []):
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ev["timestamp"] / 1000))
        print(f"CLOUDWATCH {ev['logStreamName']} {ts} {ev['message'].strip()}")
    if not resp.get("events"):
        print("CLOUDWATCH no matching log line found")


if __name__ == "__main__":
    main()
