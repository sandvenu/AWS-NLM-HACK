"""Launch a team07 SageMaker training job (eval or LoRA train) for one declared run id.

Refuses to start unless evidence/declared/<run_id>.json exists both locally and in S3,
so every job is preceded by its declaration.

  python tools/sm_launch.py eval  --run-id RID --unit knowledge --test-file knowledge_teleqna.jsonl
  python tools/sm_launch.py eval  --run-id RID --unit execution --test-file execution_telemath_synth.jsonl \
                                  --adapter-s3 s3://.../adapter/ --adapter-id team07-lora-v1
  python tools/sm_launch.py train --run-id RID --train-s3 s3://.../train/
"""
import argparse
import io
import json
import os
import tarfile
import time

import boto3

REGION = "us-east-2"
BUCKET = "bb26-p-team07-data-041915167631-use2"
ROLE = "arn:aws:iam::041915167631:role/bb26-SageMakerExecution"
IMAGE = "763104351884.dkr.ecr.us-east-2.amazonaws.com/pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker"
BASE_S3 = f"s3://{BUCKET}/nlm-track1/models/otel-llm-1.7b-it/"
TESTSETS_S3 = f"s3://{BUCKET}/nlm-track1/testsets/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def source_tarball():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in ("eval_entry.py", "train_entry.py", "requirements.txt"):
            tar.add(os.path.join(ROOT, "sagemaker", name), arcname=name)
        for name in sorted(os.listdir(os.path.join(ROOT, "src", "nlm"))):
            if name.endswith(".py"):
                tar.add(os.path.join(ROOT, "src", "nlm", name), arcname=f"nlm/{name}")
    return buf.getvalue()


def channel(name, uri):
    return {"ChannelName": name, "InputMode": "File",
            "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": uri, "S3DataDistributionType": "FullyReplicated"}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["eval", "train"])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--instance", default="ml.g6.2xlarge")
    ap.add_argument("--attempt", default="", help="suffix when relaunching the same run on another instance type")
    ap.add_argument("--unit")
    ap.add_argument("--test-file")
    ap.add_argument("--model-id", default="otel-llm-1.7b-it@2a2d417b")
    ap.add_argument("--adapter-s3", default="")
    ap.add_argument("--adapter-id", default="none")
    ap.add_argument("--train-s3", default="")
    ap.add_argument("--hp", action="append", default=[], help="extra key=value hyperparameters")
    a = ap.parse_args()

    session = boto3.Session(region_name=REGION)
    s3 = session.client("s3")
    local_decl = os.path.join(ROOT, "evidence", "declared", f"{a.run_id}.json")
    if not os.path.exists(local_decl):
        raise SystemExit(f"no local declaration {local_decl}; run tools/declare.py first")
    s3.head_object(Bucket=BUCKET, Key=f"evidence/declared/{a.run_id}.json")  # raises if not declared in S3

    code_key = f"nlm-track1/code/{a.run_id}/sourcedir.tar.gz"
    s3.put_object(Bucket=BUCKET, Key=code_key, Body=source_tarball())
    hp = {"sagemaker_program": "eval_entry.py" if a.mode == "eval" else "train_entry.py",
          "sagemaker_submit_directory": f"s3://{BUCKET}/{code_key}", "sagemaker_region": REGION,
          "run_id": a.run_id, "bucket": BUCKET}
    channels = [channel("model", BASE_S3)]
    if a.mode == "eval":
        hp.update(unit=a.unit, test_file=a.test_file, model_id=a.model_id, adapter_id=a.adapter_id)
        channels.append(channel("testsets", TESTSETS_S3))
        if a.adapter_s3:
            channels.append(channel("adapter", a.adapter_s3))
    else:
        channels.append(channel("train", a.train_s3))
    for kv in a.hp:
        k, v = kv.split("=", 1)
        hp[k] = v
    job = a.run_id + (f"-{a.attempt}" if a.attempt else "")
    sm = session.client("sagemaker")
    sm.create_training_job(
        TrainingJobName=job,
        HyperParameters={k: json.dumps(v) for k, v in hp.items()},
        AlgorithmSpecification={"TrainingImage": IMAGE, "TrainingInputMode": "File", "EnableSageMakerMetricsTimeSeries": False},
        RoleArn=ROLE,
        InputDataConfig=channels,
        OutputDataConfig={"S3OutputPath": f"s3://{BUCKET}/nlm-track1/jobs/"},
        ResourceConfig={"InstanceType": a.instance, "InstanceCount": 1, "VolumeSizeInGB": 80},
        StoppingCondition={"MaxRuntimeInSeconds": 4 * 3600 if a.mode == "train" else 2 * 3600},
        Environment={"RUN_ID": a.run_id, "PYTHONUNBUFFERED": "1"},
        Tags=[{"Key": "team", "Value": "team07"}, {"Key": "run_id", "Value": a.run_id}, {"Key": "track", "Value": "track-1"}],
    )
    print(json.dumps({"job": job, "run_id": a.run_id, "instance": a.instance, "launched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))


if __name__ == "__main__":
    main()
