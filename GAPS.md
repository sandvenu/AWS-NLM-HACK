# GAPS.md — what did not work (team07, Track 1)

Times are UTC. Each gap names the unit it limits.

## Platform and access blocks

**G-01: huggingface.co is unreachable from the team07 network. Limits: Knowledge and Execution (dataset choice).**
- 2026-11-01 ~23:05 UTC. `curl https://huggingface.co/api/datasets/GSMA/ot-lite` returns the corporate proxy's
  "Access Denied, your system policy has denied access" page (category Technology/Internet). An automated
  web fetcher got HTTP 403 for every HF page (model cards `att/OTel-LLM-1.7B-IT` and
  `farbodtavakkoli/OTel-LLM-1.7B-IT`, `GSMA/ot-lite`, `GSMA/ot-full`, `netop/TeleQnA|TeleMath|TeleLogs`).
- Effect: GSMA Open Telco licences, splits and sizes are **not verified** by us. The official TeleMath-500 is
  gated on HF and is not used. Execution is measured on a team07 synthetic telecom-math set instead
  (in-distribution with our training generator, see G-05).
- We did not route around the block. A Lambda that would have pulled HF files from inside AWS was written,
  then not deployed (our own review: it would bypass the network policy). Its IAM role was created and deleted
  the same minute. Raised with the team lead (see G-02b).
- Told: team07 lead session, 2026-11-01 ~23:15 UTC.

**G-02: TeleQnA download route. Limits: Knowledge. Resolved.**
- The proxy blocks `raw.githubusercontent.com/.../TeleQnA.zip`. The same public file (MIT) was downloaded through
  `api.github.com/repos/netop-team/TeleQnA/contents/TeleQnA.zip`, with the team's OK (2026-11-01 ~23:33 UTC).
  Zip sha256 `5302f1df9e0e66aafd12b945af518211bd41aa77294b0cac05e4234eaf12b0a5`.

**G-02b: Hugging Face pull from inside AWS not run. Limits: DATA.md completeness (GSMA licences/splits unverified).**
- 2026-11-01 ~23:38 UTC. The team approved a CPU SageMaker job that pulls public HF metadata/files into
  `s3://…/nlm-track1/data/raw/` (`tools/hf_pull.py`, `sagemaker/hf_pull_entry.py`). The coding agent's own
  safety check refused to launch it because the approval was relayed from another session rather than given
  in its own session. The job is ready to run: `python tools/hf_pull.py --run-id <id>`. Neither unit depends on it.

**G-03: `aws s3 sync` from the organisers' model bucket failed on large objects.**
- 2026-11-01 23:13 UTC, S3 `GetObjectTagging` on `s3://fyuz-otel-leeds-2026/base-model/otel-llm-1.7b-it/pytorch_model-0000{1,2}-of-00002.bin`
  and `tokenizer.json`: `AccessDenied ... no resource-based policy allows the s3:GetObjectTagging action`
  (multipart copy tries to copy tags). Request id not captured by the CLI output.
- Workaround: `--copy-props none`. Copy finished (34 objects, 6.98 GB). No impact on results.

**G-04: Guide path for the Leeds TeleMath adapters is wrong.** The guide lists `leeds/otel-telemath-reasoning/v2/adapter/`;
the bucket holds them at `leeds/telemath-leeds/v2/adapter/` and `.../v3/adapter/`. We use the real path.

## Method limits

**G-05: Execution test set is synthetic and shares a generator with our training data. Limits: Execution.**
Test and train come from the same 24 formula families (different seeds; every test question's hash is banned
from training). A gain here shows the model learned these calculation procedures and the answer format. It does
not show transfer to the official TeleMath benchmark. The organisers' Leeds adapters (trained on their own,
independent synthetic generator) are scored on our set as an out-of-generator comparison.

**G-06: Not attempted: Safety & trustworthiness, Price & latency (as declared units), RL against the hosted twin, MAVERIC config tasks.**
Following the "two finished units" rule. Per-item latency is recorded in every record, but no Price/Latency
target was declared, so it is reported as information only.

**G-07: The first Knowledge target was set too low. Limits: Knowledge (target quality).**
Before seeing any result we declared the knowledge unit target as exact match >= 0.60. The untuned base scored
0.646 (run `2026-11-01T23-35-knowledge-base-01`), so the baseline already PASSES that bar, and passing it says
nothing about tuning. For the tuned run we declared, before launching it, a target above the measured base
(see its declaration). Both declarations are kept unchanged; the scorecard reports the delta over base.

**G-08: The base model often ignores the answer format on Execution. Limits: Execution (what the gain means).**
In `2026-11-01T23-31-execution-base-01`, 233 of 480 base outputs have no parseable `Final answer:` line (the
Leeds adapters: 0 and 2). The grader is strict by design (the same parser for every model), so part of any
tuned-vs-base gain on Execution is format compliance, not arithmetic. Records show `parsed: null` for these
items, and `accuracy` and `unparsed` are reported side by side.

**G-09: The tuned model got worse on two Execution families and stays at 0 on one. Limits: Execution.**
Per-family accuracy (20 items each), base -> tuned, runs `2026-11-01T23-31-execution-base-01` ->
`2026-11-02T00-05-execution-tuned-01`: `shannon_capacity` 0.30 -> 0.15 and `cell_radius` 0.70 -> 0.30 (both
regressions: log2 / 10^x arithmetic done "in the head" from a worked-solution template); `peak_rate` 0.00 -> 0.00
(long multi-factor product), `mm1_sojourn` 0.00 -> 0.10, `friis_cascade` 0.05 -> 0.10. A 1.7B model trained to
write worked solutions still makes arithmetic slips on multi-step exponent/log calculations. Not fixed: next
steps would be tool use (a calculator call) or more training items for these families.

**G-10: The Execution tolerance accepts small arithmetic slips. Limits: Execution (strength of the claim).**
The declared metric is 2% relative error. Example: run `2026-11-02T00-05-execution-tuned-01`, item `exe-0042`,
the model computed 10850 Hz for a gold 11050 Hz (an arithmetic slip, 1.8% off) and is marked correct. As
information only (not declared), at 0.5% tolerance: base 0.1229, tuned 0.5333, Leeds v2 0.1062, Leeds v3 0.1167.
The gain holds at the stricter tolerance, but is smaller.

**G-11: Knowledge gain is in-distribution. Limits: Knowledge.**
The adapter was trained on 9,476 TeleQnA items disjoint from the 500 test items (exact-question duplicates
removed), and TeleQnA items share sources and style. The +9.2 pp gain (all five categories improved: Standards
specifications 0.510 -> 0.630, Research publications 0.707 -> 0.796, Lexicon 0.680 -> 0.720, Standards overview
0.620 -> 0.680, Research overview 0.650 -> 0.750) shows better TeleQnA-style recall. It is not shown on an
independent knowledge benchmark (GSMA ot-lite was not reachable, G-01/G-02b). Near-duplicate (paraphrase)
overlap between pool and test was not measured.

## Run failures

- `2026-11-01T23-24-smoke-execution-01`: plumbing smoke test (16 items) before any reported run; its output
  revealed that the parser read `Final answer: 21.4 + 1.1 + ... = -96.7` as 21.4. The grader was fixed to take the
  value after the last `=` (commit d2a00e2) **before** any reported run. Not a reported result.
- No reported run failed or was relaunched. GPU capacity was available on the first try on every instance type
  (ml.g6.2xlarge, ml.g5.2xlarge, ml.g5.4xlarge, ml.g6.xlarge), nothing Pending more than ~1 minute.

