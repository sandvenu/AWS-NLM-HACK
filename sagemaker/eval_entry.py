"""SageMaker entry point: evaluate one model (base, or base + LoRA adapter) on one frozen test set.

Channels:  model (base weights), testsets (frozen JSONL), adapter (optional PEFT adapter)
Hyperparameters: run_id, unit, test_file, model_id, adapter_id, bucket, batch_size, max_new_tokens

Writes, keyed by run_id:
  s3://<bucket>/evidence/records/<run_id>/records.jsonl   one line per item
  s3://<bucket>/evidence/records/<run_id>/summary.json
  CloudWatch (training job log stream): one "RECORD run_id=... item=..." line per item
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

import boto3
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, os.path.dirname(__file__))
from nlm.common import GRADER_ID, grade, messages_for, read_jsonl, sha256_file, sha256_text, summarise  # noqa: E402


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--unit", required=True, choices=["knowledge", "execution", "safety", "classify"])
    ap.add_argument("--test_file", required=True)
    ap.add_argument("--model_id", required=True)
    ap.add_argument("--adapter_id", default="none")
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--max_new_tokens", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--grader", default=GRADER_ID)
    ap.add_argument("--merge_adapter", type=int, default=0, help="1: merge the LoRA into the base weights, as served")
    ap.add_argument("--warmup", type=int, default=0, help="untimed, unrecorded generations before the first item")
    args, _ = ap.parse_known_args()

    run_id = args.run_id
    log = lambda msg: print(f"[run_id={run_id}] {msg}", flush=True)  # noqa: E731
    model_dir = os.environ.get("SM_CHANNEL_MODEL", "/opt/ml/input/data/model")
    test_path = os.path.join(os.environ.get("SM_CHANNEL_TESTSETS", "/opt/ml/input/data/testsets"), args.test_file)
    adapter_dir = os.environ.get("SM_CHANNEL_ADAPTER")
    test_sha = sha256_file(test_path)
    items = read_jsonl(test_path)
    if args.limit:
        items = items[: args.limit]
    max_new = args.max_new_tokens or {"knowledge": 24, "safety": 64, "classify": 24}.get(args.unit, 640)
    log(f"START unit={args.unit} n={len(items)} test_sha256={test_sha} model_id={args.model_id} "
        f"adapter_id={args.adapter_id} grader={args.grader} job={os.environ.get('TRAINING_JOB_NAME', '?')}")

    tok = AutoTokenizer.from_pretrained(model_dir)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, attn_implementation="sdpa").to("cuda")
    if adapter_dir and os.listdir(adapter_dir):
        from peft import PeftModel
        tarball = os.path.join(adapter_dir, "model.tar.gz")
        if os.path.exists(tarball):  # adapter produced by our own training job
            import tarfile
            adapter_dir = "/tmp/adapter"
            with tarfile.open(tarball) as tar:
                tar.extractall(adapter_dir)
        root = adapter_dir
        for dirpath, _, files in os.walk(adapter_dir):
            if "adapter_config.json" in files:
                root = dirpath
                break
        model = PeftModel.from_pretrained(model, root)
        log(f"adapter loaded from {root}")
        if args.merge_adapter:
            model = model.merge_and_unload()
            log("adapter merged into base weights")
    model.eval()
    instance_type = os.environ.get("SM_CURRENT_INSTANCE_TYPE")

    prompts = [tok.apply_chat_template(messages_for(args.unit, it, args.grader), tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False) for it in items]
    for _ in range(args.warmup):  # CUDA kernels and caches, not measured
        enc = tok([tok.apply_chat_template([{"role": "user", "content": "Say ready."}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)],
                  return_tensors="pt", add_special_tokens=False).to("cuda")
        with torch.inference_mode():
            model.generate(**enc, max_new_tokens=16, do_sample=False, temperature=None, top_p=None, top_k=None,
                           pad_token_id=tok.pad_token_id)
    if args.warmup:
        torch.cuda.synchronize()
        log(f"warmup done ({args.warmup} generations)")
    records = []
    t_all = time.time()
    for b in range(0, len(items), args.batch_size):
        batch_items, batch_prompts = items[b:b + args.batch_size], prompts[b:b + args.batch_size]
        enc = tok(batch_prompts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        started = now()
        t0 = time.time()
        with torch.inference_mode():
            out = model.generate(**enc, max_new_tokens=max_new, do_sample=False, temperature=None, top_p=None,
                                 top_k=None, pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize()
        wall = time.time() - t0
        finished = now()
        gen = out[:, enc["input_ids"].shape[1]:]
        for it, p, ids in zip(batch_items, batch_prompts, gen):
            ids = ids.tolist()
            n_tok = sum(1 for t in ids if t != tok.pad_token_id)
            text = tok.decode(ids, skip_special_tokens=True)
            rec = {"run_id": run_id, "unit": args.unit, "item_id": it["id"], "model_id": args.model_id,
                   "adapter_id": args.adapter_id, "grader": args.grader, "test_set_sha256": test_sha,
                   "prompt_sha256": sha256_text(p), "output": text, "output_sha256": sha256_text(text),
                   "output_tokens": n_tok, "truncated": n_tok >= max_new, "batch_started_at": started,
                   "batch_finished_at": finished, "batch_wall_s": round(wall, 4),
                   "latency_s": round(wall / len(batch_items), 4), "batch_size": args.batch_size,
                   "instance_type": instance_type, "adapter_merged": bool(args.merge_adapter)}
            if "task" in it:
                rec["task"] = it["task"]
            rec.update(grade(args.unit, it, text, args.grader))
            records.append(rec)
            log(f"RECORD item={it['id']} parsed={rec['parsed']} gold={rec['gold']} correct={rec['correct']} "
                f"output_sha256={rec['output_sha256']}")
        log(f"batch {b // args.batch_size + 1}: {len(records)}/{len(items)} done, {wall:.1f}s")

    summary = {"run_id": run_id, "unit": args.unit, "model_id": args.model_id, "adapter_id": args.adapter_id,
               "grader": args.grader, "test_set_sha256": test_sha, "test_file": args.test_file,
               "training_job_name": os.environ.get("TRAINING_JOB_NAME"), "instance_type": instance_type,
               "gpu": torch.cuda.get_device_name(0), "batch_size": args.batch_size, "max_new_tokens": max_new,
               "adapter_merged": bool(args.merge_adapter), "warmup": args.warmup,
               "decoding": "greedy, enable_thinking=False", "total_wall_s": round(time.time() - t_all, 2),
               "finished_at": now()}
    summary.update(summarise(args.unit, records))
    log(f"SUMMARY {json.dumps(summary)}")

    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    out_dir = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "records.jsonl"), "w", encoding="utf-8") as f:
        f.write(body)
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    s3 = boto3.client("s3")
    prefix = f"evidence/records/{run_id}"
    s3.put_object(Bucket=args.bucket, Key=f"{prefix}/records.jsonl", Body=body.encode("utf-8"))
    s3.put_object(Bucket=args.bucket, Key=f"{prefix}/summary.json", Body=json.dumps(summary, indent=2).encode())
    log(f"DONE records written to s3://{args.bucket}/{prefix}/")


if __name__ == "__main__":
    main()
