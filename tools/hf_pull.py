"""Launch the CPU SageMaker job that pulls public Hugging Face dataset metadata/files into
s3://bb26-p-team07-data-041915167631-use2/nlm-track1/data/raw/ (see sagemaker/hf_pull_entry.py).

  python tools/hf_pull.py --run-id 2026-11-01T23-40-datapull-01
"""
import argparse
import io
import json
import os
import tarfile

import boto3

REGION = "us-east-2"
BUCKET = "bb26-p-team07-data-041915167631-use2"
ROLE = "arn:aws:iam::041915167631:role/bb26-SageMakerExecution"
IMAGE = "763104351884.dkr.ecr.us-east-2.amazonaws.com/pytorch-training:2.8.0-cpu-py312-ubuntu22.04-sagemaker"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--instance", default="ml.m5.large")
    a = ap.parse_args()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(os.path.join(ROOT, "sagemaker", "hf_pull_entry.py"), arcname="hf_pull_entry.py")
        req = "huggingface_hub>=0.34\n".encode()
        ti = tarfile.TarInfo("requirements.txt")
        ti.size = len(req)
        tar.addfile(ti, io.BytesIO(req))
    key = f"nlm-track1/code/{a.run_id}/sourcedir.tar.gz"
    session = boto3.Session(region_name=REGION)
    session.client("s3").put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    hp = {"sagemaker_program": "hf_pull_entry.py", "sagemaker_submit_directory": f"s3://{BUCKET}/{key}",
          "sagemaker_region": REGION, "bucket": BUCKET, "run_id": a.run_id}
    session.client("sagemaker").create_training_job(
        TrainingJobName=a.run_id,
        HyperParameters={k: json.dumps(v) for k, v in hp.items()},
        AlgorithmSpecification={"TrainingImage": IMAGE, "TrainingInputMode": "File"},
        RoleArn=ROLE,
        OutputDataConfig={"S3OutputPath": f"s3://{BUCKET}/nlm-track1/jobs/"},
        ResourceConfig={"InstanceType": a.instance, "InstanceCount": 1, "VolumeSizeInGB": 50},
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
        Tags=[{"Key": "team", "Value": "team07"}, {"Key": "run_id", "Value": a.run_id}],
    )
    print(json.dumps({"job": a.run_id, "instance": a.instance}))


if __name__ == "__main__":
    main()
