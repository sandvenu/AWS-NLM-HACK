"""SageMaker entry point: LoRA SFT of OTel-LLM-1.7B-IT (recipe follows OTel training/llm/peft).

Channels: model (base weights), train (train.jsonl: {"messages": [...], "source": ...})
Output:   /opt/ml/model/adapter (PEFT adapter) + train_summary.json, also copied to
          s3://<bucket>/evidence/records/<run_id>/train_summary.json
Loss is completion-only: tokens outside the assistant turn are masked (-100).
"""
import argparse
import datetime as dt
import json
import os
import random
import time

import boto3
import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, TrainerCallback, set_seed


def build_example(messages, tok):
    kw = dict(tokenize=True, return_dict=False, enable_thinking=False)
    ids = tok.apply_chat_template(messages, add_generation_prompt=False, **kw)
    labels = [-100] * len(ids)
    for i, m in enumerate(messages):
        if m["role"] != "assistant":
            continue
        start = len(tok.apply_chat_template(messages[:i], add_generation_prompt=True, **kw))
        end = len(tok.apply_chat_template(messages[: i + 1], add_generation_prompt=False, **kw))
        labels[start:end] = ids[start:end]
    return {"input_ids": ids, "labels": labels}


def collate_fn(pad_id):
    def collate(feats):
        w = max(len(f["input_ids"]) for f in feats)
        return {
            "input_ids": torch.tensor([f["input_ids"] + [pad_id] * (w - len(f["input_ids"])) for f in feats]),
            "labels": torch.tensor([f["labels"] + [-100] * (w - len(f["labels"])) for f in feats]),
            "attention_mask": torch.tensor([[1] * len(f["input_ids"]) + [0] * (w - len(f["input_ids"])) for f in feats]),
        }
    return collate


class LogCallback(TrainerCallback):
    def __init__(self, run_id):
        self.run_id = run_id

    def on_log(self, args, state, control, logs=None, **kw):
        print(f"[run_id={self.run_id}] TRAINLOG step={state.global_step} {json.dumps(logs or {})}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--lora_r", type=int, default=32)
    ap.add_argument("--lora_alpha", type=int, default=64)
    ap.add_argument("--lora_dropout", type=float, default=0.05)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--grad_acc", type=int, default=2)
    ap.add_argument("--max_seq_len", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=42)
    args, _ = ap.parse_known_args()
    run_id = args.run_id
    log = lambda m: print(f"[run_id={run_id}] {m}", flush=True)  # noqa: E731
    set_seed(args.seed)

    model_dir = os.environ.get("SM_CHANNEL_MODEL", "/opt/ml/input/data/model")
    train_path = os.path.join(os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"), "train.jsonl")
    out_dir = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")

    tok = AutoTokenizer.from_pretrained(model_dir)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    rows, dropped = [], 0
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ex = build_example(json.loads(line)["messages"], tok)
            if len(ex["input_ids"]) > args.max_seq_len or all(l == -100 for l in ex["labels"]):
                dropped += 1
                continue
            rows.append(ex)
    random.Random(args.seed).shuffle(rows)
    log(f"START train rows={len(rows)} dropped={dropped} job={os.environ.get('TRAINING_JOB_NAME')}")

    model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.bfloat16, attn_implementation="sdpa")
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout,
                                             target_modules="all-linear", task_type="CAUSAL_LM"))
    model.print_trainable_parameters()

    targs = TrainingArguments(
        output_dir="/opt/ml/checkpoints", num_train_epochs=args.epochs, per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_acc, learning_rate=args.lr, lr_scheduler_type="cosine",
        warmup_ratio=0.03, logging_steps=10, save_strategy="no", bf16=True, report_to=[], seed=args.seed,
        group_by_length=True, remove_unused_columns=False, dataloader_num_workers=2)
    t0 = time.time()
    trainer = Trainer(model=model, args=targs, train_dataset=rows, data_collator=collate_fn(tok.pad_token_id),
                      callbacks=[LogCallback(run_id)])
    result = trainer.train()
    adapter_dir = os.path.join(out_dir, "adapter")
    model.save_pretrained(adapter_dir)
    tok.save_pretrained(adapter_dir)

    summary = {"run_id": run_id, "training_job_name": os.environ.get("TRAINING_JOB_NAME"),
               "instance_type": os.environ.get("SM_CURRENT_INSTANCE_TYPE"), "gpu": torch.cuda.get_device_name(0),
               "train_rows": len(rows), "dropped_rows": dropped, "hyperparameters": vars(args),
               "train_loss": result.training_loss, "train_runtime_s": round(time.time() - t0, 1),
               "log_history": trainer.state.log_history,
               "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    with open(os.path.join(out_dir, "train_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    boto3.client("s3").put_object(Bucket=args.bucket, Key=f"evidence/records/{run_id}/train_summary.json",
                                  Body=json.dumps(summary, indent=2).encode())
    log(f"DONE loss={result.training_loss:.4f} adapter={adapter_dir}")


if __name__ == "__main__":
    main()
