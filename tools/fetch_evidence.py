"""Copy per-run evidence (records, summaries) from the team07 bucket into evidence/records/.

  python tools/fetch_evidence.py <run_id> [<run_id> ...]
"""
import os
import sys

import boto3

BUCKET = "bb26-p-team07-data-041915167631-use2"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    s3 = boto3.client("s3", region_name="us-east-2")
    for run_id in sys.argv[1:]:
        prefix = f"evidence/records/{run_id}/"
        objs = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix).get("Contents", [])
        if not objs:
            print(f"{run_id}: no evidence in s3://{BUCKET}/{prefix}")
            continue
        for o in objs:
            dest = os.path.join(ROOT, o["Key"].replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            s3.download_file(BUCKET, o["Key"], dest)
            print(f"{run_id}: {o['Key']} ({o['Size']} bytes)")


if __name__ == "__main__":
    main()
