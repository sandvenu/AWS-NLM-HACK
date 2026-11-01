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
  the same minute. Raised with the team lead for a decision.
- Told: team07 lead session, 2026-11-01 ~23:15 UTC.

**G-02: TeleQnA download route (pending decision). Limits: Knowledge.**
- The proxy blocks `raw.githubusercontent.com/.../TeleQnA.zip`. The same public file (MIT) downloads through
  `api.github.com/repos/netop-team/TeleQnA/contents/TeleQnA.zip`
  (sha256 of the zip recorded in DATA.md once used). Awaiting the team's OK before using that copy.

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

## Run failures

(none yet)
