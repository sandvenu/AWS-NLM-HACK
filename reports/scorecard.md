# team07 Track 1 scorecard (rebuilt from evidence/)

| unit | role | run id | model / adapter | n | accuracy | target | check | times agree with AWS | p50 latency (s/item) |
|---|---|---|---|---|---|---|---|---|---|
| knowledge | base | `2026-11-01T23-35-knowledge-base-01` | otel-llm-1.7b-it@2a2d417b / none | 500 | 0.6460 | exact_match >= 0.6 | PASS | True | 0.0445 |
| knowledge | tuned | `2026-11-02T00-05-knowledge-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 500 | 0.7380 | exact_match >= 0.68 | PASS | True | 0.0416 |
| knowledge | tuned_v2 | `2026-11-02T09-00-knowledge-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 500 | 0.7520 | exact_match >= 0.68 | PASS | True | 0.0317 |
| knowledge | tuned_v3 | `2026-11-02T11-30-knowledge-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 500 | 0.7220 | exact_match >= 0.68 | PASS | True | 0.0317 |
| knowledge | **tuned - base** | | | | **+0.0920** | | | | |
| execution | base | `2026-11-01T23-31-execution-base-01` | otel-llm-1.7b-it@2a2d417b / none | 480 | 0.1500 | accuracy_rel2pct >= 0.6 | FAIL | True | 1.6224 |
| execution | tuned | `2026-11-02T00-05-execution-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 480 | 0.6792 | accuracy_rel2pct >= 0.6 | PASS | True | 0.2991 |
| execution | leeds_v2 | `2026-11-01T23-31-execution-leedsv2-01` | otel-llm-1.7b-it@2a2d417b / leeds-telemath-v2 | 480 | 0.1292 | accuracy_rel2pct >= 0.6 | FAIL | True | 0.1917 |
| execution | leeds_v3 | `2026-11-01T23-31-execution-leedsv3-01` | otel-llm-1.7b-it@2a2d417b / leeds-telemath-v3 | 480 | 0.1542 | accuracy_rel2pct >= 0.6 | FAIL | True | 0.2237 |
| execution | tuned_v2 | `2026-11-02T09-00-execution-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 480 | 0.7042 | accuracy_rel2pct >= 0.6 | PASS | True | 0.3 |
| execution | tuned_v3 | `2026-11-02T11-30-execution-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 480 | 0.7312 | accuracy_rel2pct >= 0.6 | PASS | True | 0.2973 |
| execution | **tuned - base** | | | | **+0.5292** | | | | |
| knowledge_ood_oranbench | base | `2026-11-02T00-55-oranbench-base-01` | otel-llm-1.7b-it@2a2d417b / none | 1500 | 0.6720 | exact_match >= 0.65 | PASS | True | 0.042 |
| knowledge_ood_oranbench | tuned | `2026-11-02T00-55-oranbench-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 1500 | 0.7060 | exact_match >= 0.65 | PASS | True | 0.0444 |
| knowledge_ood_oranbench | tuned_v2 | `2026-11-02T09-00-oranbench-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 1500 | 0.7053 | exact_match >= 0.65 | PASS | True | 0.0322 |
| knowledge_ood_oranbench | tuned_v3 | `2026-11-02T11-30-oranbench-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 1500 | 0.7147 | exact_match >= 0.65 | PASS | True | 0.0321 |
| knowledge_ood_oranbench | **tuned - base** | | | | **+0.0340** | | | | |
| execution_ood_telemath_gsma_protocol | base | `2026-11-02T00-29-telemath-gsma-base-01` | otel-llm-1.7b-it@2a2d417b / none | 500 | 0.0080 | accuracy_gsma_rule >= 0.1 | FAIL | True | 4.3848 |
| execution_ood_telemath_gsma_protocol | tuned | `2026-11-02T00-29-telemath-gsma-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 500 | 0.0620 | accuracy_gsma_rule >= 0.1 | FAIL | True | 2.7273 |
| execution_ood_telemath_gsma_protocol | tuned_v2 | `2026-11-02T09-00-telemath-gsma-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 500 | 0.1060 | accuracy_gsma_rule >= 0.1 | PASS | True | 4.5522 |
| execution_ood_telemath_gsma_protocol | tuned_v2_2k_tokens | `2026-11-02T10-20-telemath-gsma-v2-2k-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 500 | 0.1060 | accuracy_gsma_rule >= 0.11 | FAIL | True | 12.5409 |
| execution_ood_telemath_gsma_protocol | tuned_v3 | `2026-11-02T11-30-telemath-gsma-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 500 | 0.1040 | accuracy_gsma_rule >= 0.1 | PASS | True | 4.6383 |
| execution_ood_telemath_gsma_protocol | tuned_v2_vote5 | `2026-11-02T11-30-telemath-gsma-v2-vote5-02` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 500 | 0.1060 | accuracy_gsma_rule >= 0.13 | FAIL | True | 4.0403 |
| execution_ood_telemath_gsma_protocol | **tuned - base** | | | | **+0.0540** | | | | |
| execution_ood_telemath_team07_protocol | base | `2026-11-02T00-29-telemath-team07-base-01` | otel-llm-1.7b-it@2a2d417b / none | 500 | 0.0400 | accuracy_rel2pct >= 0.1 | FAIL | True | 1.9965 |
| execution_ood_telemath_team07_protocol | tuned | `2026-11-02T00-29-telemath-team07-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 500 | 0.0700 | accuracy_rel2pct >= 0.1 | FAIL | True | 3.7447 |
| execution_ood_telemath_team07_protocol | **tuned - base** | | | | **+0.0300** | | | | |
| price_latency | base | `2026-11-02T07-16-pricelat-base-01` | otel-llm-1.7b-it@2a2d417b / none | 120 | 0.1250 | latency_p95_s <= 5.0; cost_per_1k_correct_usd <= 1.5 | FAIL | True | 2.1475 |
| price_latency | tuned | `2026-11-02T07-16-pricelat-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1-merged | 120 | 0.6833 | latency_p95_s <= 5.0; cost_per_1k_correct_usd <= 1.5 | PASS | True | 1.6794 |
| price_latency | tuned_v2 | `2026-11-02T09-00-pricelat-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2-merged | 120 | 0.7333 | latency_p95_s <= 5.0; cost_per_1k_correct_usd <= 1.5 | PASS | True | 1.6978 |
| price_latency | tuned_v3 | `2026-11-02T11-30-pricelat-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3-merged | 120 | 0.7583 | latency_p95_s <= 5.0; cost_per_1k_correct_usd <= 1.5 | PASS | True | 1.6671 |
| price_latency | **tuned - base** | | | | **+0.5583** | | | | |
| safety | base | `2026-11-02T07-50-safety-base-01` | otel-llm-1.7b-it@2a2d417b / none | 480 | 0.5125 | accuracy >= 0.7; flag_recall >= 0.8; false_alarm_rate <= 0.2 | FAIL | True | 0.1326 |
| safety | tuned | `2026-11-02T08-00-safety-tuned-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v1 | 480 | 0.6188 | accuracy >= 0.4925; flag_recall >= 0.6925; harmful_refusal_rate >= 0.95 | FAIL | True | 0.1435 |
| safety | tuned_v2 | `2026-11-02T09-00-safety-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 480 | 0.9062 | accuracy >= 0.7; flag_recall >= 0.8; false_alarm_rate <= 0.2; harmful_refusal_rate >= 0.95 | PASS | True | 0.0874 |
| safety | tuned_v3 | `2026-11-02T11-30-safety-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 480 | 0.8667 | accuracy >= 0.7; flag_recall >= 0.8; false_alarm_rate <= 0.2; harmful_refusal_rate >= 0.95 | FAIL | True | 0.159 |
| safety | **tuned - base** | | | | **+0.1063** | | | | |
| knowledge_ood_srsranbench | base | `2026-11-02T08-30-srsran-base-01` | otel-llm-1.7b-it@2a2d417b / none | 1502 | 0.7410 | exact_match >= 0.5 | PASS | True | 0.0381 |
| knowledge_ood_srsranbench | tuned_v2 | `2026-11-02T09-00-srsran-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 1502 | 0.7636 | exact_match >= 0.721 | PASS | True | 0.0353 |
| knowledge_ood_srsranbench | tuned_v3 | `2026-11-02T11-30-srsran-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 1502 | 0.7570 | exact_match >= 0.721 | PASS | True | 0.0356 |
| classify_ood_3gpp_tsg | base | `2026-11-02T08-30-tsg-base-01` | otel-llm-1.7b-it@2a2d417b / none | 2000 | 0.1975 | accuracy >= 0.2 | FAIL | True | 0.1157 |
| classify_ood_3gpp_tsg | tuned_v2 | `2026-11-02T09-00-tsg-v2-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v2 | 2000 | 0.2425 | accuracy >= 0.2 | PASS | True | 0.3721 |
| classify_ood_3gpp_tsg | tuned_v3 | `2026-11-02T11-30-tsg-v3-01` | otel-llm-1.7b-it@2a2d417b / team07-lora-v3 | 2000 | 0.2255 | accuracy >= 0.2 | PASS | True | 0.3721 |

Execution, information only (not declared): accuracy within 0.5% relative error: base 0.1229, tuned 0.5333, leeds_v2 0.1062, leeds_v3 0.1167, tuned_v2 0.5687, tuned_v3 0.5938.

Price/Latency detail (batch 1, greedy, same items, prompt and parser; cost = on-demand Hosting price x wall time, evidence/pricing.json):

| role | instance | adapter merged | p50 s | p95 s | mean s | tokens/s | accuracy | USD per 1k requests | USD per 1k correct |
|---|---|---|---|---|---|---|---|---|---|
| base | ml.g6.2xlarge ($1.222/h) | False | 2.1475 | 6.7153 | 2.8552 | 36.94 | 0.1250 | 0.9692 | 7.7534 |
| tuned | ml.g6.2xlarge ($1.222/h) | True | 1.6794 | 3.6511 | 1.953 | 36.73 | 0.6833 | 0.663 | 0.9702 |
| tuned_v2 | ml.g6.2xlarge ($1.222/h) | True | 1.6978 | 3.6564 | 1.9758 | 36.22 | 0.7333 | 0.6707 | 0.9145 |
| tuned_v3 | ml.g6.2xlarge ($1.222/h) | True | 1.6671 | 3.5807 | 1.9303 | 37.04 | 0.7583 | 0.6552 | 0.864 |

Declared runs that failed (no records, no score; reported, not dropped):

- `2026-11-02T10-20-telemath-gsma-v2-vote5-01`: CUDA out of memory on ml.g5.2xlarge (batch 8 x 5 samples x 2,048 tokens); no records. Re-declared as 2026-11-02T11-30-telemath-gsma-v2-vote5-02.

Rebuild: `python tools/rebuild.py` (no AWS access; exits 1 if any evidence changed).
