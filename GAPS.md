# GAPS.md — what did not work (team07, Track 1)

Times are UTC. Each gap names the unit it limits.

## Platform and access blocks

**G-01: huggingface.co is unreachable from the team07 network. Limits: Knowledge and Execution (dataset choice).**
- 2026-11-01 ~23:05 UTC. `curl https://huggingface.co/api/datasets/GSMA/ot-lite` returns the corporate proxy's
  "Access Denied, your system policy has denied access" page (category Technology/Internet). An automated
  web fetcher got HTTP 403 for every HF page (model cards `att/OTel-LLM-1.7B-IT` and
  `farbodtavakkoli/OTel-LLM-1.7B-IT`, `GSMA/ot-lite`, `GSMA/ot-full`, `netop/TeleQnA|TeleMath|TeleLogs`).
- Effect: the Execution unit is measured on a team07 synthetic telecom-math set (in-distribution with our training
  generator, see G-05). Resolved later for the out-of-distribution checks: the user downloaded `GSMA/ot-full`
  (revision 6319806f...) and shared it as a zip (2026-11-02 ~00:23 UTC), giving the official TeleMath and ORAN-Bench
  test splits (G-12, G-13). `netop/TeleMath` itself stays gated (the user's account sees only the card images).
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
not show transfer to the official TeleMath benchmark (G-12 measures that transfer, and it is small). The organisers' Leeds adapters (trained on their own,
independent synthetic generator) are scored on our set as an out-of-generator comparison.

**G-06: Not attempted: Safety & trustworthiness, RL against the hosted twin, MAVERIC config tasks.**
Following the "two finished units" rule. Price & latency was added later as a third unit (G-16). RL against the
hosted twin waits on the organisers' team .env (twin URL and adapter token); we may not host our own twin for the event.

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

**G-12: The Execution gain mostly does not transfer to the official TeleMath benchmark. Limits: Execution.**
Official TeleMath test split (500, `GSMA/ot-full`), never trained on, declared before the runs with prediction tuned >= 0.10:
- team07 prompt and parser (2%): base 0.040 -> tuned 0.070 (`2026-11-02T00-29-telemath-team07-base-01` ->
  `2026-11-02T00-29-telemath-team07-tuned-01`). Target missed: FAIL.
- GSMA official prompt and scorer (`gsma-evals-telemath@708f1c5`): base 0.008 -> tuned 0.062
  (`2026-11-02T00-29-telemath-gsma-base-01` -> `2026-11-02T00-29-telemath-gsma-tuned-01`). Target missed: FAIL.
  The base model left no `\boxed{}` answer in 454/500 outputs (388 of them not truncated: it ignores the format);
  the tuned model in 210/500 (109 hit the 1,024-token limit). For comparison, the organisers report the Leeds
  adapters at 5.8% (v2) and 4.2% (v3) on official TeleMath with their own 5% scorer (not rerun by us).

So the +52.9 pp on our synthetic set is mostly learned procedure and answer format for our 24 families. On real
TeleMath (multi-step probability, queueing, information theory) the tuned 1.7B model gains only 3 to 5 pp.
The GSMA scorer also uses `abs_tol=0.01`, so an answer counts as correct whenever |pred - gold| <= 0.01, even when
the gold itself is tiny (e.g. 7.2e-05). We ported it verbatim and did not correct this.

**G-13: ORAN-Bench target set too low; the gain is modest. Limits: Knowledge (out of distribution).**
Official ORAN-Bench test split (1,500 O-RAN MCQs, never trained on): base 0.672 -> tuned 0.706 (+3.4 pp), runs
`2026-11-02T00-55-oranbench-base-01` -> `2026-11-02T00-55-oranbench-tuned-01`. The declared target (>= 0.65) was
below the base, so both PASS and the check says nothing about tuning (as in G-07). The evidence is the +3.4 pp
delta: TeleQnA training transfers a little to O-RAN questions.

**G-14: One job waited 22 minutes for a GPU.** `2026-11-02T00-29-telemath-gsma-tuned-01` on ml.g5.2xlarge was
created 00:29 UTC and started downloading at 00:51 UTC. Under the 30-minute rule, so not relaunched. No other job
waited more than about a minute.

**G-16: Price/Latency unit: what it does and does not measure. Limits: Price/Latency.**
Runs `2026-11-02T07-16-pricelat-base-01` (FAIL) -> `2026-11-02T07-16-pricelat-tuned-01` (PASS), both declared before launch with the same two targets
(p95 latency <= 5.0 s and <= $1.50 per 1,000 correct answers).
- Items: the first 120 of the frozen Execution set (5 per family, all 24 families), not all 480, to keep one-at-a-time
  runs short. Knowledge items were not timed (answers are 1 to 20 tokens, so latency says little there).
- Serving stack: Hugging Face `generate`, batch size 1, on a SageMaker training job (ml.g6.2xlarge, one NVIDIA L4).
  Not a real endpoint: no network, queueing or concurrency. A serving engine such as vLLM would be faster for both models.
- Cost is the on-demand Hosting price x busy time only. It ignores idle time, so it is a lower bound for a
  dedicated endpoint; the base/tuned ratio is the useful number.
- The tuned model runs with the LoRA merged into the weights (`merge_adapter=1`). Unmerged PEFT, as in the
  Execution unit runs, decodes more slowly. Accuracy on these 120 items (0.683) equals the unmerged tuned Execution run on
  the same items, and 116 of 120 verdicts are identical, so merging barely changes answers.
- Tuned and base decode at the same speed (about 37 tokens/s); the gain comes from shorter answers and higher accuracy.

## Run failures

- `2026-11-01T23-24-smoke-execution-01`: plumbing smoke test (16 items) before any reported run; its output
  revealed that the parser read `Final answer: 21.4 + 1.1 + ... = -96.7` as 21.4. The grader was fixed to take the
  value after the last `=` (commit d2a00e2) **before** any reported run. Not a reported result.
- No reported run failed or was relaunched (one 22-minute Pending wait, G-14).
- `tools/rebuild.py` first mis-graded the ORAN-Bench records: it graded unit `knowledge-ood` with the numeric
  parser. The stored verdicts were right and the rebuild tool was fixed. No record or declaration was changed.


## Publication limits

**G-15: Official TeleMath per-item records are not in the public repository.** They contain the TeleMath answer
key (the gold value per item) and model outputs that restate the problems; the TeleMath authors ask that the data
not be redistributed. The four runs' `records.jsonl` stay in the team bucket at
`s3://bb26-p-team07-data-041915167631-use2/evidence/records/<run_id>/records.jsonl` (readable by the live-test
command); their declarations and `summary.json` are in Git. Offline `tools/rebuild.py` therefore reports these four
runs from `summary.json` without re-grading them. The ORAN-Bench and team07 test-set records are in Git and are
re-graded offline.
