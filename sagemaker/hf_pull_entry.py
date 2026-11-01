"""SageMaker entry point (CPU): record metadata for public Hugging Face datasets and copy the
non-gated, redistributable files into the team07 bucket.

Approved by the team (2026-11-01): the team07 laptop network blocks huggingface.co, so the
pull runs inside AWS. TeleLogs files are never downloaded (the publisher asks not to
redistribute). Gated repos are recorded as gated and skipped.

Output: s3://<bucket>/nlm-track1/data/raw/<repo_id>/...  and  .../hf_pull_report.json
"""
import argparse
import hashlib
import json
import os

import boto3
from huggingface_hub import HfApi, hf_hub_download

INFO_ONLY = ["GSMA/ot-full", "netop/TeleQnA", "netop/TeleMath", "netop/TeleLogs"]
DOWNLOAD = ["GSMA/ot-lite"]
MAX_FILE_BYTES = 300 * 1024 * 1024


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--run_id", required=True)
    args, _ = ap.parse_known_args()
    api, s3 = HfApi(), boto3.client("s3")
    prefix = "nlm-track1/data/raw"
    report = {"run_id": args.run_id, "repos": {}}
    for repo in INFO_ONLY + DOWNLOAD:
        entry = {}
        try:
            info = api.dataset_info(repo, files_metadata=True)
            entry.update(sha=info.sha, gated=info.gated, private=info.private,
                         licence=(info.card_data or {}).get("license") if info.card_data else None,
                         configs=(info.card_data or {}).get("configs") if info.card_data else None,
                         files=[{"path": s.rfilename, "size": s.size} for s in info.siblings or []])
        except Exception as e:  # gated or missing repos are recorded, not fatal
            entry["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            report["repos"][repo] = entry
            print(f"[run_id={args.run_id}] {repo}: {entry['error']}", flush=True)
            continue
        try:
            card = hf_hub_download(repo, "README.md", repo_type="dataset", revision=info.sha)
            s3.upload_file(card, args.bucket, f"{prefix}/{repo}/README.md")
            entry["readme_sha256"] = sha256(card)
        except Exception as e:
            entry["readme_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        if repo in DOWNLOAD and not info.gated:
            entry["downloaded"] = []
            for f in entry["files"]:
                p = f["path"]
                if "telelogs" in p.lower() or (f["size"] or 0) > MAX_FILE_BYTES or p == "README.md":
                    continue
                local = hf_hub_download(repo, p, repo_type="dataset", revision=info.sha)
                s3.upload_file(local, args.bucket, f"{prefix}/{repo}/{p}")
                entry["downloaded"].append({"path": p, "sha256": sha256(local), "size": f["size"]})
        report["repos"][repo] = entry
        print(f"[run_id={args.run_id}] {repo}: sha={entry.get('sha')} gated={entry.get('gated')} "
              f"licence={entry.get('licence')} files={len(entry.get('files', []))} "
              f"downloaded={len(entry.get('downloaded', []))}", flush=True)
    body = json.dumps(report, indent=2, default=str)
    s3.put_object(Bucket=args.bucket, Key=f"{prefix}/hf_pull_report.json", Body=body.encode())
    os.makedirs("/opt/ml/model", exist_ok=True)
    with open("/opt/ml/model/hf_pull_report.json", "w") as f:
        f.write(body)
    print(f"[run_id={args.run_id}] DONE", flush=True)


if __name__ == "__main__":
    main()
