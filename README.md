Primary track: track-1 (NLM training and production readiness), team07 <!-- TODO(team07): confirm the primary track; the team's main entry may be Track 3, which would make this repo a secondary submission -->

# team07 — OTel-LLM-1.7B-IT: LoRA fine-tune with an evidence-chain scorecard

**Problem (three lines).** General LLMs do well on telecom "interface" tasks but poorly on execution tasks
(calculations, configuration). Operators need to show a risk owner that a tuned NLM is actually better than the
model it came from. We LoRA-tune the OTel 1.7B base on SageMaker and score base vs tuned on frozen test sets, with a declared target, one run id per run and a rule-based grader.

## Architecture

```
frozen test sets (Git, SHA-256)        tools/declare.py ──► evidence/declared/<run_id>.json  (local + S3, write-once)
  testsets/*.jsonl + MANIFEST.json                │
                                                  ▼
 s3://…-use2/nlm-track1/models/otel-llm-1.7b-it  tools/sm_launch.py ──► SageMaker training job named <run_id>
 (server-side copy of organisers' base, us-east-1)   (eval_entry.py | train_entry.py, PyTorch 2.8 DLC, ml.g6/g5)
                                                  │
                         per-item records + summary ─► s3://…/evidence/records/<run_id>/   (+ CloudWatch "RECORD run_id=…" lines)
                                                  │
                         tools/fetch_evidence.py ─► evidence/records/<run_id>/  ─► tools/rebuild.py ─► reports/scorecard.{md,json}
```

- **Knowledge**: TeleQnA multiple choice, 500 items stratified by category, exact match on the option letter.
- **Execution**: 480 synthetic telecom-math problems (24 formula families), numeric answer within 2% relative error
  (5% also reported).
- **Grader**: `rule-based-parser-v1` (`src/nlm/common.py`). No LLM grades anything.
- **Same conditions**: every model gets the same prompts (`messages_for`), the same chat template with thinking off,
  greedy decoding and the same parser.

## One command per stage

Environment: `AWS_PROFILE=fyuz`, region us-east-2, Python ≥ 3.11 with `boto3` (we run everything through `uv run --with boto3 python …`).

| Stage | Command |
|---|---|
| Build Execution test set | `python -m nlm.telemath_gen --seed 7101 --n 480 --prefix exe --out testsets/execution_telemath_synth.jsonl` (with `PYTHONPATH=src`) |
| Build Knowledge test set + train pool | `python tools/build_knowledge.py --teleqna data/raw/TeleQnA.txt --test-out testsets/knowledge_teleqna.jsonl --pool-out data/train/teleqna_pool.jsonl` |
| Freeze (hash) | `python tools/freeze.py testsets/<file> --unit … --source … --licence … --build …` |
| Build training data | `python tools/build_train.py --exec-n 6000 --teleqna-pool data/train/teleqna_pool.jsonl --know-n 6000` |
| Declare a run | `python tools/declare.py --run-id <run_id> --unit <unit> --metric <m> --value <v> --test-file testsets/<file> --model-id … --adapter-id …` |
| Evaluate (SageMaker) | `python tools/sm_launch.py eval --run-id <run_id> --unit <unit> --test-file <file> [--adapter-s3 s3://…/adapter/ --adapter-id …]` |
| Fine-tune (SageMaker) | `python tools/sm_launch.py train --run-id <run_id> --train-s3 s3://…/nlm-track1/train/<run_id>/` |
| Pull evidence | `python tools/fetch_evidence.py <run_id> …` |
| **Rebuild scorecard (no AWS)** | `python tools/rebuild.py` (`--write` to regenerate `reports/scorecard.*`) |
| Live test (read-only) | `python tools/show_record.py --run-id <run_id> --item <item_id>` (S3 GetObject + CloudWatch Logs reads only) |
| Grader tests | `python tests/test_grader.py` |

## Results

| Unit | Metric | Untuned base | Tuned (team07-lora-v1) | Delta | Declared target (tuned) | Check |
|---|---|---|---|---|---|---|
| Knowledge (TeleQnA, 500) | exact match | 0.646 | **0.738** | +9.2 pp | >= 0.68 | PASS |
| Execution (synthetic telecom math, 480) | within 2% rel. error | 0.150 | **0.679** | +52.9 pp | >= 0.60 | PASS |
| Price/Latency (first 120 Execution items, one request at a time, ml.g6.2xlarge) | p95 latency <= 5.0 s **and** <= $1.50 per 1,000 correct answers | 6.72 s, $7.75 (FAIL) | **3.65 s, $0.97** | -3.06 s, -$6.78 | both | PASS |

Price/Latency detail (runs `2026-11-02T07-16-pricelat-base-01` -> `2026-11-02T07-16-pricelat-tuned-01`): greedy, batch size 1, 2 untimed warm-ups, tuned adapter merged
into the base weights as it would be served. Cost = SageMaker on-demand Hosting price from the AWS Price List API
(`evidence/pricing.json`, $1.222/h for ml.g6.2xlarge in us-east-2) x per-request wall time.

| | p50 s | p95 s | mean s | tokens/s | accuracy (2%) | USD per 1k requests | USD per 1k correct |
|---|---|---|---|---|---|---|---|
| base | 2.15 | 6.72 | 2.86 | 36.9 | 0.125 | 0.97 | 7.75 |
| tuned | 1.68 | 3.65 | 1.95 | 36.7 | 0.683 | 0.66 | 0.97 |

Decoding speed is the same (about 37 tokens/s): merging the LoRA adds no serving cost. The tuned model is faster and
cheaper because it writes shorter answers (it learned the `Final answer:` format), and it is right far more often,
so a correct answer costs 8x less. Limits in GAPS G-16.

**Out-of-distribution checks** (official `GSMA/ot-full` test splits, never trained on, hashes frozen, files kept out of Git):

| Test | Protocol | Base | Tuned | Delta | Declared prediction | Check |
|---|---|---|---|---|---|---|
| ORAN-Bench (1,500 MCQ) | team07 knowledge prompt, exact match | 0.672 | 0.706 | +3.4 pp | >= 0.65 | PASS (base passes too, GAPS G-13) |
| Official TeleMath (500) | GSMA official prompt + scorer (gsma-labs/evals@708f1c5) | 0.008 | 0.062 | +5.4 pp | >= 0.10 | FAIL |
| Official TeleMath (500) | team07 prompt + parser, 2% | 0.040 | 0.070 | +3.0 pp | >= 0.10 | FAIL |

The large synthetic Execution gain mostly does **not** transfer to real TeleMath (GAPS G-12).

The organisers' Leeds TeleMath LoRAs on the same Execution set: v2 0.129, v3 0.154. At a stricter 0.5% tolerance
(information only) tuned 0.533 vs base 0.123. Run ids: knowledge `2026-11-01T23-35-knowledge-base-01` ->
`2026-11-02T00-05-knowledge-tuned-01`; execution `2026-11-01T23-31-execution-base-01` ->
`2026-11-02T00-05-execution-tuned-01`; training `2026-11-01T23-39-train-lora-01`. Read the caveats in GAPS.md
(G-05, G-07 to G-11): Execution is in-distribution with our training generator, and part of its gain is answer-format compliance.

See [`reports/scorecard.md`](reports/scorecard.md) (rebuilt from `evidence/` by `tools/rebuild.py`),
[`GAPS.md`](GAPS.md) for what did not work and [`DATA.md`](DATA.md) for data lineage.

## Before Nov 1

Nothing in this repository existed before the event. It was started on 2026-11-01 (UTC) during the
hackathon. Reused, with credit: the OTel PEFT recipe structure (github.com/farbodtavakkoli/OTel,
Apache-2.0, `training/llm/peft`); the organisers' base model and Leeds adapters (used read-only); the TeleMath-style system prompt from the organisers' Leeds code package (`code/common_reasoning.py`).
