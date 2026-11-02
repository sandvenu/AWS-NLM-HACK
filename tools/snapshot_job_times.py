"""Save what AWS recorded for each run's SageMaker job (read-only DescribeTrainingJob) to
evidence/aws_job_times.json, so tools/rebuild.py can check offline that every record's
timestamps fall inside its job's AWS training window.

  python tools/snapshot_job_times.py
"""
import json
import os

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    runs = json.load(open(os.path.join(ROOT, "reports", "runs.json"), encoding="utf-8"))
    run_ids = [runs["training_run"], runs.get("training_run_v2"), runs.get("training_run_v3"), runs.get("training_run_v4")] + [r for roles in runs["units"].values() for r in roles.values()]
    run_ids = [r for r in run_ids if r]
    sm = boto3.client("sagemaker", region_name="us-east-2")
    out = {}
    for rid in run_ids:
        j = sm.describe_training_job(TrainingJobName=rid)
        out[rid] = {"training_job_name": j["TrainingJobName"], "training_job_arn": j["TrainingJobArn"],
                    "status": j["TrainingJobStatus"], "instance_type": j["ResourceConfig"]["InstanceType"],
                    "creation_time": j["CreationTime"].isoformat(), "training_start_time": j["TrainingStartTime"].isoformat(),
                    "training_end_time": j["TrainingEndTime"].isoformat(),
                    "billable_seconds": j.get("BillableTimeInSeconds"),
                    "tags_run_id": rid}
    with open(os.path.join(ROOT, "evidence", "aws_job_times.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
