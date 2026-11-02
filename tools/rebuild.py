"""Rebuild the scorecard from evidence/ with no AWS access.

For every run listed in reports/runs.json it:
  1. checks the frozen test set still matches testsets/MANIFEST.json and the run's declaration;
  2. re-grades every per-item record from its raw output with the rule-based grader,
     and checks the stored output hash and verdict;
  3. recomputes the unit metrics and the pass/fail check against the declared target.
Exits 1 if anything changed or disagrees. With --write it also writes reports/scorecard.{json,md}.

  python tools/rebuild.py [--write]
"""
import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from nlm.common import GRADER_ID, grade, num_correct, price_latency, read_jsonl, sha256_file, sha256_text, summarise  # noqa: E402

_times_path = os.path.join(ROOT, "evidence", "aws_job_times.json")
AWS_TIMES = json.load(open(_times_path, encoding="utf-8")) if os.path.exists(_times_path) else {}
PRICES = json.load(open(os.path.join(ROOT, "evidence", "pricing.json"), encoding="utf-8"))["usd_per_hour"]
METRIC_KEY = {"exact_match": "accuracy", "accuracy_rel2pct": "accuracy", "accuracy_gsma_rule": "accuracy", "accuracy_rel5pct": "accuracy_loose_5pct"}


def check_one(t, summary):
    value = summary.get(METRIC_KEY.get(t["metric"], t["metric"]))
    if value is None:
        return None, None
    ok = value >= t["value"] if t.get("direction", ">=") == ">=" else value <= t["value"]
    return value, "PASS" if ok else "FAIL"


def check_target(decl, summary):
    """Primary target value, and PASS only if the primary and every also_target pass."""
    value, verdict = check_one(decl["target"], summary)
    for t in decl.get("also_targets", []):
        if check_one(t, summary)[1] != "PASS":
            verdict = "FAIL"
    return value, verdict


def summary_only(run_id, decl, manifest, errors):
    """Runs whose per-item records hold a non-redistributable answer key: records stay in S3
    (s3://<bucket>/evidence/records/<run_id>/records.jsonl); report the committed summary."""
    summary = json.load(open(os.path.join(ROOT, "evidence", "records", run_id, "summary.json"), encoding="utf-8"))
    if summary["test_set_sha256"] != decl["test_set_sha256"] or manifest.get(decl["test_set"], {}).get("sha256") != decl["test_set_sha256"]:
        errors.append(f"{run_id}: summary/declaration/MANIFEST test-set hashes disagree")
    value, verdict = check_target(decl, summary)
    keep = {k: summary[k] for k in ("n", "accuracy", "unparsed", "latency_p50_s", "latency_p95_s") if k in summary}
    return {"run_id": run_id, "unit": decl["unit"], "model_id": decl["model_id"], "adapter_id": decl["adapter_id"],
            "target": decl["target"], "declared_at": decl["declared_at"], "test_set_sha256": decl["test_set_sha256"],
            "metric_value": value, "check": verdict, "times_agree_with_aws": "records in S3 only",
            "grader": decl["grader"], "test_set": decl["test_set"],
            "test_set_check": "records in S3 only (answer key not redistributable); summary reported, not re-graded offline",
            **keep}


def rebuild_run(run_id, manifest, errors, s3_only=()):
    decl = json.load(open(os.path.join(ROOT, "evidence", "declared", f"{run_id}.json"), encoding="utf-8"))
    rec_path = os.path.join(ROOT, "evidence", "records", run_id, "records.jsonl")
    if not os.path.exists(rec_path):
        if run_id in s3_only:
            return summary_only(run_id, decl, manifest, errors)
        errors.append(f"{run_id}: no records at {rec_path}")
        return None
    test_rel = decl["test_set"]
    test_path = os.path.join(ROOT, test_rel)
    records = read_jsonl(rec_path)
    gunit = decl.get("grading_unit") or decl["unit"].removesuffix("-ood")  # knowledge-ood is graded like knowledge
    if manifest.get(test_rel, {}).get("sha256") != decl["test_set_sha256"]:
        errors.append(f"{run_id}: declared test-set hash does not match testsets/MANIFEST.json")
    if os.path.exists(test_path):
        actual = sha256_file(test_path)
        if actual != decl["test_set_sha256"]:
            errors.append(f"{run_id}: test set {test_rel} hash {actual} != declared {decl['test_set_sha256']}")
        test_items = read_jsonl(test_path)
        if decl.get("limit"):
            test_items = test_items[: decl["limit"]]
            if [r["item_id"] for r in records] != [it["id"] for it in test_items]:
                errors.append(f"{run_id}: records are not the first {decl['limit']} test items in order")
        items = {it["id"]: it for it in test_items}
        test_set_check = "hash verified" + (f", first {decl['limit']} items" if decl.get("limit") else "")
    else:
        # Test sets kept out of Git (licence terms, see DATA.md): re-grade against the gold stored in each record.
        items = {r["item_id"]: {"id": r["item_id"], "answer": r["gold"]} for r in records}
        test_set_check = "file not in repo; hash in MANIFEST, gold taken from records"
    regraded = []
    for r in records:
        if r["run_id"] != run_id:
            errors.append(f"{run_id}: record {r['item_id']} carries run_id {r['run_id']}")
        if sha256_text(r["output"]) != r["output_sha256"]:
            errors.append(f"{run_id}: record {r['item_id']} output hash mismatch")
        g = grade(gunit, items[r["item_id"]], r["output"], decl["grader"])
        if g["correct"] != r["correct"]:
            errors.append(f"{run_id}: record {r['item_id']} verdict {r['correct']} != regraded {g['correct']}")
        regraded.append({**r, **g})
    if len(records) != len(items):
        errors.append(f"{run_id}: {len(records)} records for {len(items)} test items")
    times_ok = None
    aws = AWS_TIMES.get(run_id)
    if aws:
        lo, hi = dt.datetime.fromisoformat(aws["training_start_time"]), dt.datetime.fromisoformat(aws["training_end_time"])
        declared = dt.datetime.fromisoformat(decl["declared_at"])
        times_ok = declared <= dt.datetime.fromisoformat(aws["creation_time"]) and all(
            lo <= dt.datetime.fromisoformat(r["batch_started_at"]) <= dt.datetime.fromisoformat(r["batch_finished_at"]) <= hi
            for r in records)
        if not times_ok:
            errors.append(f"{run_id}: record times or declaration time disagree with AWS job times")
    summary = summarise(gunit, regraded)
    if gunit == "execution" and decl["grader"] == GRADER_ID:  # information only, not a declared metric
        summary["info_accuracy_rel0_5pct"] = round(
            sum(num_correct(r["parsed"], r["gold"], 0.005) for r in regraded) / len(regraded), 4)
    if decl["unit"] == "price-latency":
        itypes = {r["instance_type"] for r in records}
        if len(itypes) != 1 or {r["batch_size"] for r in records} != {1}:
            errors.append(f"{run_id}: price-latency records must come from one instance type at batch size 1")
        itype = itypes.pop()
        summary.update(instance_type=itype, adapter_merged=records[0]["adapter_merged"],
                       **price_latency(regraded, PRICES[itype]))
    value, verdict = check_target(decl, summary)
    return {"run_id": run_id, "unit": decl["unit"], "model_id": decl["model_id"], "adapter_id": decl["adapter_id"],
            "target": decl["target"], "also_targets": decl.get("also_targets", []), "declared_at": decl["declared_at"],
            "test_set_sha256": decl["test_set_sha256"],
            "metric_value": value, "check": verdict, "times_agree_with_aws": times_ok, "grader": decl["grader"],
            "test_set": test_rel, "test_set_check": test_set_check, **summary}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    manifest = json.load(open(os.path.join(ROOT, "testsets", "MANIFEST.json"), encoding="utf-8"))["files"]
    for rel, meta in manifest.items():
        path = os.path.join(ROOT, rel)
        if os.path.exists(path) and sha256_file(path) != meta["sha256"]:
            print(f"ERROR frozen test set changed: {rel}")
            sys.exit(1)
    runs = json.load(open(os.path.join(ROOT, "reports", "runs.json"), encoding="utf-8"))
    errors, card = [], {"units": {}}
    for unit, roles in runs["units"].items():
        card["units"][unit] = {}
        for role, run_id in roles.items():
            res = rebuild_run(run_id, manifest, errors, runs.get("s3_only_records", []))
            if res:
                card["units"][unit][role] = res
        base, tuned = card["units"][unit].get("base"), card["units"][unit].get("tuned")
        if base and tuned:
            card["units"][unit]["delta_accuracy"] = round(tuned["accuracy"] - base["accuracy"], 4)

    lines = ["# team07 Track 1 scorecard (rebuilt from evidence/)", "",
             "| unit | role | run id | model / adapter | n | accuracy | target | check | times agree with AWS | p50 latency (s/item) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for unit, roles in card["units"].items():
        for role, r in roles.items():
            if not isinstance(r, dict):
                continue
            t = r["target"]
            lines.append(f"| {unit} | {role} | `{r['run_id']}` | {r['model_id']} / {r['adapter_id']} | {r['n']} | "
                         f"{r['accuracy']:.4f} | {'; '.join(f"{x['metric']} {x.get('direction', '>=')} {x['value']}" for x in [t, *r.get('also_targets', [])])} | {r['check']} | "
                         f"{r['times_agree_with_aws']} | "
                         f"{r.get('latency_p50_s', '')} |")
        if "delta_accuracy" in roles:
            lines.append(f"| {unit} | **tuned - base** | | | | **{roles['delta_accuracy']:+.4f}** | | | | |")
    lines += ["", "Execution, information only (not declared): accuracy within 0.5% relative error: " + ", ".join(
        f"{role} {r['info_accuracy_rel0_5pct']:.4f}" for role, r in card["units"].get("execution", {}).items()
        if isinstance(r, dict) and "info_accuracy_rel0_5pct" in r) + "."]
    pl = card["units"].get("price_latency", {})
    if pl:
        lines += ["", "Price/Latency detail (batch 1, greedy, same items, prompt and parser; cost = on-demand Hosting price x wall time, "
                  "evidence/pricing.json):", "",
                  "| role | instance | adapter merged | p50 s | p95 s | mean s | tokens/s | accuracy | USD per 1k requests | USD per 1k correct |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for role, r in pl.items():
            if isinstance(r, dict):
                lines.append(f"| {role} | {r['instance_type']} (${r['usd_per_hour']}/h) | {r['adapter_merged']} | {r['latency_p50_s']} | "
                             f"{r['latency_p95_s']} | {r['latency_mean_s']} | {r['tokens_per_s']} | {r['accuracy']:.4f} | "
                             f"{r['cost_per_1k_requests_usd']} | {r['cost_per_1k_correct_usd']} |")
    text = "\n".join(lines)
    print(text)
    if args.write:
        with open(os.path.join(ROOT, "reports", "scorecard.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(card, f, indent=2)
        with open(os.path.join(ROOT, "reports", "scorecard.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n\nRebuild: `python tools/rebuild.py` (no AWS access; exits 1 if any evidence changed).\n")
    if errors:
        print("\nERRORS:\n" + "\n".join(errors))
        sys.exit(1)
    s3_only = [r for r in runs.get("s3_only_records", [])
               if not os.path.exists(os.path.join(ROOT, "evidence", "records", r, "records.jsonl"))]
    note = f" ({len(s3_only)} official-TeleMath runs reported from summary.json; records in S3 only)" if s3_only else ""
    print("\nrebuild OK: every committed record re-graded and matched; test-set hashes match declarations" + note)


if __name__ == "__main__":
    main()
