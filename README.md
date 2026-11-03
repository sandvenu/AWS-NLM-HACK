Primary track: track-1 (NLM training and production readiness), team07

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
| Demo walkthrough (recorded) | `python tools/demo.py` (script and narration in [DEMO.md](DEMO.md)) |

## Results

**Submitted adapter: `team07-lora-v2`** (training run `2026-11-02T08-40-train-lora-02`). v1 is kept as the first
iteration: it passed Knowledge, Execution and Price/Latency but failed Safety, so v2 added safety and GSMA-format
examples to the training mix (DATA.md). Every number below has a target declared before its run.

| Unit | Metric | Untuned base | v1 | **v2 (submitted)** | Declared target (v2) | v2 check |
|---|---|---|---|---|---|---|
| Knowledge (TeleQnA, 500) | exact match | 0.646 | 0.738 | **0.752** | >= 0.68 | PASS |
| Execution (synthetic telecom math, 480) | within 2% rel. error | 0.150 | 0.679 | **0.704** | >= 0.60 | PASS |
| Price/Latency (first 120 Execution items, batch 1, ml.g6.2xlarge) | p95 latency; USD per 1,000 correct | 6.72 s; $7.75 | 3.65 s; $0.97 | **3.66 s; $0.91** | <= 5.0 s and <= $1.50 | PASS |
| Safety & trustworthiness (480 synthetic) | accuracy; flag recall; false alarms; harmful refusal | 0.513; 0.713; 0.688; 1.00 | 0.619; 0.504; 0.267; 0.925 | **0.906; 0.908; 0.096; 1.00** | >= 0.70; >= 0.80; <= 0.20; >= 0.95 | PASS |

Base runs fail Execution, Price/Latency and Safety targets; v1 failed Safety (it was less safe than the base: GAPS
G-17). v2 refuses all 80 harmful requests, including 10/10 requests to silently drop emergency calls (a topic never
in its training data; v1 accepted 6 of them), and helps with all 80 legitimate look-alikes. It still misses most
breaches of the step-size rule (P3: 6/27) and wrongly flags 23 of 160 safe changes (GAPS G-18).

Run ids (base -> v1 -> v2): knowledge `2026-11-01T23-35-knowledge-base-01` -> `2026-11-02T00-05-knowledge-tuned-01` ->
`2026-11-02T09-00-knowledge-v2-01`; execution `2026-11-01T23-31-execution-base-01` -> `2026-11-02T00-05-execution-tuned-01` ->
`2026-11-02T09-00-execution-v2-01`; price/latency `2026-11-02T07-16-pricelat-base-01` -> `2026-11-02T07-16-pricelat-tuned-01` ->
`2026-11-02T09-00-pricelat-v2-01`; safety `2026-11-02T07-50-safety-base-01` -> `2026-11-02T08-00-safety-tuned-01` ->
`2026-11-02T09-00-safety-v2-01`.

Price/Latency detail (runs `2026-11-02T07-16-pricelat-base-01` -> `2026-11-02T07-16-pricelat-tuned-01`): greedy, batch size 1, 2 untimed warm-ups, tuned adapter merged
into the base weights as it would be served. Cost = SageMaker on-demand Hosting price from the AWS Price List API
(`evidence/pricing.json`, $1.222/h for ml.g6.2xlarge in us-east-2) x per-request wall time.

| | p50 s | p95 s | mean s | tokens/s | accuracy (2%) | USD per 1k requests | USD per 1k correct |
|---|---|---|---|---|---|---|---|
| base | 2.15 | 6.72 | 2.86 | 36.9 | 0.125 | 0.97 | 7.75 |
| v1 | 1.68 | 3.65 | 1.95 | 36.7 | 0.683 | 0.66 | 0.97 |
| v2 | 1.70 | 3.66 | 1.98 | 36.2 | 0.733 | 0.67 | 0.91 |

Decoding speed is the same (about 37 tokens/s): merging the LoRA adds no serving cost. The tuned model is faster and
cheaper because it writes shorter answers (it learned the `Final answer:` format), and it is right far more often,
so a correct answer costs 8x less. Limits in GAPS G-16.

**Out-of-distribution checks** (official `GSMA/ot-full` test splits, never trained on, hashes frozen, files kept out of Git):

| Test | Protocol | Base | v1 | **v2** | Declared target (v2) | v2 check |
|---|---|---|---|---|---|---|
| Official TeleMath (500) | GSMA official prompt + scorer (gsma-labs/evals@708f1c5) | 0.008 | 0.062 | **0.106** | >= 0.10 | PASS (by 3 items, GAPS G-12) |
| ORAN-Bench (1,500 MCQ) | team07 knowledge prompt, exact match | 0.672 | 0.706 | **0.705** | >= 0.65 | PASS (base passes too, G-13) |
| srsRAN-Bench (1,502 MCQ, options shuffled) | team07 knowledge prompt, exact match | 0.741 | - | **0.764** | >= 0.721 (no regression) | PASS |
| 3GPP-TSG (2,000, 16 working groups) | benchmark prompt verbatim, label exact match | 0.198 | - | **0.243** | >= 0.20 | PASS |
| Official TeleMath (500) | team07 prompt + parser, 2% | 0.040 | 0.070 | - | >= 0.10 | v1 FAIL (not rerun for v2) |

v2's TeleMath gain is mostly answer format: outputs with no `\boxed{}` number fell from 210 (v1) to 24, and correct
answers rose from 31 to 53 of 500. It is 3 items above the target, so it is a narrow pass (GAPS G-12).

After v2, three declared attempts to go further were run and reported (GAPS G-19): a 2,048-token limit and a
5-sample vote on official TeleMath (both 0.106, both FAIL their higher targets), and a LoRA v3 that gained on
Execution (0.731) and ORAN-Bench (0.715) but failed Safety (harmful refusal 0.625) and lost 3 points on Knowledge.
A rebalanced LoRA v4 also failed three targets (Safety, official TeleMath, 3GPP-TSG). The rule fixed before the runs was "replace v2 only if no unit regresses", so v2 stays submitted.

The organisers' Leeds TeleMath LoRAs on the same Execution set: v2 0.129, v3 0.154. At a stricter 0.5% tolerance
(information only) base 0.123, v1 0.533, team07 v2 0.569. Training runs: v1 `2026-11-01T23-39-train-lora-01`, v2
`2026-11-02T08-40-train-lora-02`. Read the caveats in GAPS.md
(G-05, G-07 to G-11): Execution is in-distribution with our training generator, and part of its gain is answer-format compliance.

See [`reports/scorecard.md`](reports/scorecard.md) (rebuilt from `evidence/` by `tools/rebuild.py`),
[`GAPS.md`](GAPS.md) for what did not work and [`DATA.md`](DATA.md) for data lineage.

## Before Nov 1

Nothing in this repository existed before the event. It was started on 2026-11-01 (UTC) during the
hackathon. Reused, with credit: the OTel PEFT recipe structure (github.com/farbodtavakkoli/OTel,
Apache-2.0, `training/llm/peft`); the organisers' base model and Leeds adapters (used read-only); the TeleMath-style system prompt from the organisers' Leeds code package (`code/common_reasoning.py`).
