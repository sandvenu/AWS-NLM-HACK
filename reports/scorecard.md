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

Execution, information only (not declared): accuracy within 0.5% relative error: base 0.1229, tuned 0.5333, leeds_v2 0.1062, leeds_v3 0.1167.

Rebuild: `python tools/rebuild.py` (no AWS access; exits 1 if any evidence changed).
