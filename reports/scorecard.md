# team07 Track 1 scorecard (rebuilt from evidence/)

| unit | role | run id | model / adapter | n | accuracy | target | check | times agree with AWS | p50 latency (s/item) |
|---|---|---|---|---|---|---|---|---|---|
| knowledge | base | `2026-11-01T23-35-knowledge-base-01` | otel-llm-1.7b-it@2a2d417b / none | 500 | 0.6460 | exact_match >= 0.6 | PASS | True | 0.0445 |
| knowledge | tuned | `2026-11-02T00-05-knowledge-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 500 | 0.7380 | exact_match >= 0.68 | PASS | True | 0.0416 |
| knowledge | **tuned - base** | | | | **+0.0920** | | | | |
| execution | base | `2026-11-01T23-31-execution-base-01` | otel-llm-1.7b-it@2a2d417b / none | 480 | 0.1500 | accuracy_rel2pct >= 0.6 | FAIL | True | 1.6224 |
| execution | tuned | `2026-11-02T00-05-execution-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 480 | 0.6792 | accuracy_rel2pct >= 0.6 | PASS | True | 0.2991 |
| execution | leeds_v2 | `2026-11-01T23-31-execution-leedsv2-01` | otel-llm-1.7b-it@2a2d417b / leeds-telemath-v2 | 480 | 0.1292 | accuracy_rel2pct >= 0.6 | FAIL | True | 0.1917 |
| execution | leeds_v3 | `2026-11-01T23-31-execution-leedsv3-01` | otel-llm-1.7b-it@2a2d417b / leeds-telemath-v3 | 480 | 0.1542 | accuracy_rel2pct >= 0.6 | FAIL | True | 0.2237 |
| execution | **tuned - base** | | | | **+0.5292** | | | | |
| knowledge_ood_oranbench | base | `2026-11-02T00-55-oranbench-base-01` | otel-llm-1.7b-it@2a2d417b / none | 1500 | 0.6720 | exact_match >= 0.65 | PASS | True | 0.042 |
| knowledge_ood_oranbench | tuned | `2026-11-02T00-55-oranbench-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 1500 | 0.7060 | exact_match >= 0.65 | PASS | True | 0.0444 |
| knowledge_ood_oranbench | **tuned - base** | | | | **+0.0340** | | | | |
| execution_ood_telemath_gsma_protocol | base | `2026-11-02T00-29-telemath-gsma-base-01` | otel-llm-1.7b-it@2a2d417b / none | 500 | 0.0080 | accuracy_gsma_rule >= 0.1 | FAIL | True | 4.3848 |
| execution_ood_telemath_gsma_protocol | tuned | `2026-11-02T00-29-telemath-gsma-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 500 | 0.0620 | accuracy_gsma_rule >= 0.1 | FAIL | True | 2.7273 |
| execution_ood_telemath_gsma_protocol | **tuned - base** | | | | **+0.0540** | | | | |
| execution_ood_telemath_team07_protocol | base | `2026-11-02T00-29-telemath-team07-base-01` | otel-llm-1.7b-it@2a2d417b / none | 500 | 0.0400 | accuracy_rel2pct >= 0.1 | FAIL | True | 1.9965 |
| execution_ood_telemath_team07_protocol | tuned | `2026-11-02T00-29-telemath-team07-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 500 | 0.0700 | accuracy_rel2pct >= 0.1 | FAIL | True | 3.7447 |
| execution_ood_telemath_team07_protocol | **tuned - base** | | | | **+0.0300** | | | | |
| price_latency | base | `2026-11-02T07-16-pricelat-base-01` | otel-llm-1.7b-it@2a2d417b / none | 120 | 0.1250 | latency_p95_s <= 5.0; cost_per_1k_correct_usd <= 1.5 | FAIL | True | 2.1475 |
| price_latency | tuned | `2026-11-02T07-16-pricelat-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1-merged | 120 | 0.6833 | latency_p95_s <= 5.0; cost_per_1k_correct_usd <= 1.5 | PASS | True | 1.6794 |
| price_latency | **tuned - base** | | | | **+0.5583** | | | | |
| safety | base | `2026-11-02T07-50-safety-base-01` | otel-llm-1.7b-it@2a2d417b / none | 480 | 0.5125 | accuracy >= 0.7; flag_recall >= 0.8; false_alarm_rate <= 0.2 | FAIL | True | 0.1326 |
| safety | tuned | `2026-11-02T08-00-safety-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 480 | 0.6188 | accuracy >= 0.4925; flag_recall >= 0.6925; harmful_refusal_rate >= 0.95 | FAIL | True | 0.1435 |
| safety | **tuned - base** | | | | **+0.1063** | | | | |

Execution, information only (not declared): accuracy within 0.5% relative error: base 0.1229, tuned 0.5333, leeds_v2 0.1062, leeds_v3 0.1167.

Price/Latency detail (batch 1, greedy, same items, prompt and parser; cost = on-demand Hosting price x wall time, evidence/pricing.json):

| role | instance | adapter merged | p50 s | p95 s | mean s | tokens/s | accuracy | USD per 1k requests | USD per 1k correct |
|---|---|---|---|---|---|---|---|---|---|
| base | ml.g6.2xlarge ($1.222/h) | False | 2.1475 | 6.7153 | 2.8552 | 36.94 | 0.1250 | 0.9692 | 7.7534 |
| tuned | ml.g6.2xlarge ($1.222/h) | True | 1.6794 | 3.6511 | 1.953 | 36.73 | 0.6833 | 0.663 | 0.9702 |

Rebuild: `python tools/rebuild.py` (no AWS access; exits 1 if any evidence changed).
