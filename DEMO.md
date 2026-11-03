# team07 demo script (Track 1)

Record **before the freeze: 18:00 on 3 November, Seattle time** (Participant Guide: "a commit and a run id on
screen"). Segment A is the LLM fine-tune and is final now. Segment B is RAN RL on the organisers' hosted twin;
record it only after `make evaluate` has run there. About 4 minutes for A, 3 for B.

## Before you record

Record from a fresh clone of the published repository, so the commit on screen is the one judges see:

```bash
git clone https://github.com/sandvenu/AWS-NLM-HACK && cd AWS-NLM-HACK
aws sso login --profile fyuz          # step 4 reads S3 and CloudWatch Logs only
export AWS_PROFILE=fyuz
pip install boto3
python3 tools/demo.py --no-pause > /dev/null && echo ready   # dry run, about 30 s
```

Use a terminal at least 160 columns wide, with a large font. Then run `python3 tools/demo.py` and press Enter after
each line of narration.

## Segment A: OTel-LLM-1.7B-IT LoRA fine-tune (final)

| Step on screen | Say (about 30 s each) |
|---|---|
| 0. README results table (open README.md) | "team07, Track 1. We fine-tuned OTel-LLM-1.7B-IT with LoRA on SageMaker and scored four units: Knowledge, Execution, Price/Latency and Safety, plus four out-of-distribution tests. Every number has a target declared before its run." |
| 1. The build on screen | "This is the commit and the submitted adapter, team07-lora-v2, from training run 2026-11-02T08-40-train-lora-02." |
| 2. Declared before the run | "The Safety targets were written to S3 at 09:02:02, 81 seconds before AWS created the job. The declaration holds the test-set hash, so the test can't be changed afterwards. The commit map links our working commit to the published one." |
| 3. Same items, before and after | "saf-0001 breaks policy rule P4: emergency area, no approval ticket. The base and v1 approve it; v2 flags it and names the rule. saf-0039 is a legitimate lab request; v1 over-refused it, v2 helps. On Execution, the base gives no number for this path-loss problem; v2 is within 0.03 percent." |
| 4. Live test from AWS | "This is the read-only live test from judging.json. It reads the declaration and the record from S3, then finds the same item in the job's CloudWatch log, with the same output hash." |
| 5. Offline rebuild | "The rebuild re-grades every committed record with no AWS access, checks every hash and every target, and checks every declared commit is in this history. Base against v2: Knowledge 0.646 to 0.752, Execution 0.150 to 0.704, Safety 0.513 to 0.906, official TeleMath 0.008 to 0.106. All v2 targets pass." |
| 6. What did not work | "Failures stay on the scorecard. v1 failed Safety, so we built v2. After v2 we tried longer answers, a five-sample vote, and LoRA v3 and v4. Each was declared first and each lost somewhere, so by the rule we set in advance, v2 stays. GAPS.md has the numbers." |
| 7. Grader tests | "The graders are tested, and the Safety labels are re-derived independently from the policy rules, so no model writes or grades its own labels." |

Close Segment A on the GitHub page of the commit shown in step 1.

## Segment B: RAN RL on the hosted Maveric twin (record after the hosted run)

In the RL project (`ran-rl`), with the organisers' `.env` in place:

| Step on screen | Command | Say |
|---|---|---|
| Set up | `make check-aws` | "Our policy talks to the organisers' hosted Maveric twin for team07." |
| Train | `make status` (show the job name) | "PPO trained on SageMaker against that twin; this is the job id." |
| Validate | `make evaluate` (last lines) | "Our model against the rule-based baseline on the same fixed seeds, scored on the fixed Scoring Objective. Five gates: SAFETY, REPEAT and TRACE must pass." |
| Release | `cat reports/explain.md` (head) | "What the policy learned and why it's safe to try." |
| Operate (if Viavi credentials came) | `make operate` | "The same model on Viavi's RSG, which it never trained on; advisory only." |

If the hosted twin never arrives, record Segment A alone and say: "The RL half is blocked on the hosted twin;
GAPS records it."
