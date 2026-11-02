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
from nlm.common import grade, num_correct, read_jsonl, sha256_file, sha256_text, summarise  # noqa: E402

_times_path = os.path.join(ROOT, "evidence", "aws_job_times.json")
AWS_TIMES = json.load(open(_times_path, encoding="utf-8")) if os.path.exists(_times_path) else {}
METRIC_KEY = {"exact_match": "accuracy", "accuracy_rel2pct": "accuracy", "accuracy_rel5pct": "accuracy_loose_5pct"}


def check_target(decl, summary):
    t = decl["target"]
    value = summary.get(METRIC_KEY.get(t["metric"], t["metric"]))
    if value is None:
        return None, None
    ok = value >= t["value"] if t.get("direction", ">=") == ">=" else value <= t["value"]
    return value, "PASS" if ok else "FAIL"


def rebuild_run(run_id, manifest, errors):
    decl = json.load(open(os.path.join(ROOT, "evidence", "declared", f"{run_id}.json"), encoding="utf-8"))
    rec_path = os.path.join(ROOT, "evidence", "records", run_id, "records.jsonl")
    if not os.path.exists(rec_path):
        errors.append(f"{run_id}: no records at {rec_path}")
        return None
    test_rel = decl["test_set"]
    test_path = os.path.join(ROOT, test_rel)
    actual = sha256_file(test_path)
    if actual != decl["test_set_sha256"]:
        errors.append(f"{run_id}: test set {test_rel} hash {actual} != declared {decl['test_set_sha256']}")
    if manifest.get(test_rel, {}).get("sha256") != actual:
        errors.append(f"{run_id}: test set {test_rel} does not match testsets/MANIFEST.json")
    items = {it["id"]: it for it in read_jsonl(test_path)}
    records = read_jsonl(rec_path)
    regraded = []
    for r in records:
        if r["run_id"] != run_id:
            errors.append(f"{run_id}: record {r['item_id']} carries run_id {r['run_id']}")
        if sha256_text(r["output"]) != r["output_sha256"]:
            errors.append(f"{run_id}: record {r['item_id']} output hash mismatch")
        g = grade(decl["unit"], items[r["item_id"]], r["output"])
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
    summary = summarise(decl["unit"], regraded)
    if decl["unit"] == "execution":  # information only, not a declared metric
        summary["info_accuracy_rel0_5pct"] = round(
            sum(num_correct(r["parsed"], r["gold"], 0.005) for r in regraded) / len(regraded), 4)
    value, verdict = check_target(decl, summary)
    return {"run_id": run_id, "unit": decl["unit"], "model_id": decl["model_id"], "adapter_id": decl["adapter_id"],
            "target": decl["target"], "declared_at": decl["declared_at"], "test_set_sha256": decl["test_set_sha256"],
            "metric_value": value, "check": verdict, "times_agree_with_aws": times_ok, **summary}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    manifest = json.load(open(os.path.join(ROOT, "testsets", "MANIFEST.json"), encoding="utf-8"))["files"]
    for rel, meta in manifest.items():
        if sha256_file(os.path.join(ROOT, rel)) != meta["sha256"]:
            print(f"ERROR frozen test set changed: {rel}")
            sys.exit(1)
    runs = json.load(open(os.path.join(ROOT, "reports", "runs.json"), encoding="utf-8"))
    errors, card = [], {"units": {}}
    for unit, roles in runs["units"].items():
        card["units"][unit] = {}
        for role, run_id in roles.items():
            res = rebuild_run(run_id, manifest, errors)
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
                         f"{r['accuracy']:.4f} | {t['metric']} {t.get('direction', '>=')} {t['value']} | {r['check']} | "
                         f"{r['times_agree_with_aws']} | "
                         f"{r.get('latency_p50_s', '')} |")
        if "delta_accuracy" in roles:
            lines.append(f"| {unit} | **tuned - base** | | | | **{roles['delta_accuracy']:+.4f}** | | | | |")
    lines += ["", "Execution, information only (not declared): accuracy within 0.5% relative error: " + ", ".join(
        f"{role} {r['info_accuracy_rel0_5pct']:.4f}" for role, r in card["units"].get("execution", {}).items()
        if isinstance(r, dict) and "info_accuracy_rel0_5pct" in r) + "."]
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
    print("\nrebuild OK: every record re-graded and matched; test-set hashes match declarations")


if __name__ == "__main__":
    main()
