"""Recorded demo walkthrough: every screen comes from the repository's evidence or a read-only AWS call.

Shows the commit and run ids on screen (Participant Guide: "a commit and a run id on screen"), then walks one
unit's evidence chain: declared target -> AWS job -> per-item record -> offline re-grade -> pass/fail.
Press Enter between steps (--no-pause to run straight through; --skip-aws for the offline steps only).

  python tools/demo.py            # needs boto3 and the fyuz AWS profile for step 4
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = json.load(open(os.path.join(ROOT, "reports", "runs.json"), encoding="utf-8"))
TIMES = json.load(open(os.path.join(ROOT, "evidence", "aws_job_times.json"), encoding="utf-8"))
SAFETY_V2 = RUNS["units"]["safety"]["tuned_v2"]


def say(title):
    print("\n" + "=" * 100 + f"\n  {title}\n" + "=" * 100)


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True).stdout.strip()


def records(run_id):
    path = os.path.join(ROOT, "evidence", "records", run_id, "records.jsonl")
    return {r["item_id"]: r for r in map(json.loads, open(path, encoding="utf-8"))}


def questions(name):
    return {q["id"]: q for q in map(json.loads, open(os.path.join(ROOT, "testsets", name), encoding="utf-8"))}


def first_line(text, n=110):
    return " ".join(text.split())[:n]


def step_build():
    say("1. The build on screen")
    print(f"commit     {git('rev-parse', 'HEAD')}")
    print(f"           {git('log', '-1', '--format=%s')}")
    print(f"remote     {git('remote', 'get-url', 'origin') or '(working repository)'}")
    print(f"shown at   {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
    print(f"submitted  adapter team07-lora-v2 from training run {RUNS['training_run_v2']} on OTel-LLM-1.7B-IT")


def step_declared():
    say(f"2. The target was declared before the run: {SAFETY_V2}")
    decl = json.load(open(os.path.join(ROOT, "evidence", "declared", f"{SAFETY_V2}.json"), encoding="utf-8"))
    mapping = json.load(open(os.path.join(ROOT, "evidence", "commit_map.json"), encoding="utf-8"))["working_to_published"]
    print("declared targets  " + "; ".join(f"{t['metric']} {t.get('direction', '>=')} {t['value']}"
                                         for t in [decl["target"], *decl.get("also_targets", [])]))
    print(f"test set sha256   {decl['test_set_sha256']}  ({decl['test_set']})")
    print(f"declared at       {decl['declared_at']}  from commit {decl['git_commit'][:7]}"
          f" (published {mapping.get(decl['git_commit'], decl['git_commit'])[:7]}, evidence/commit_map.json)")
    job = TIMES[SAFETY_V2]
    created = dt.datetime.fromisoformat(job["creation_time"])
    lead = created - dt.datetime.fromisoformat(decl["declared_at"])
    print(f"AWS job created   {created.astimezone(dt.timezone.utc):%Y-%m-%dT%H:%M:%S}+00:00 on {job['instance_type']}"
          f"  -> declared {int(lead.total_seconds() // 60)} min {int(lead.total_seconds() % 60)} s earlier")


def step_items():
    say("3. Same test items, before and after fine-tuning (committed per-item records)")
    saf = questions("safety_ran.jsonl")
    runs = RUNS["units"]["safety"]
    base, v1, v2 = records(runs["base"]), records(runs["tuned"]), records(runs["tuned_v2"])
    for item, why in [("saf-0001", "a change that breaks policy rule P4 (emergency area, no ticket)"),
                      ("saf-0039", "a legitimate lab-test request that v1 refused")]:
        print(f"\n{item}: {why}\n  question  {first_line(saf[item]['question'], 160)}")
        for name, recs in [("base", base), ("v1", v1), ("v2", v2)]:
            r = recs[item]
            print(f"  {name:<5} {'RIGHT' if r['correct'] else 'WRONG'}  {first_line(r['output'])}")
        print(f"  gold      {v2[item]['gold']}")
    exe = questions("execution_telemath_synth.jsonl")
    runs = RUNS["units"]["execution"]
    b, t = records(runs["base"])["exe-0001"], records(runs["tuned_v2"])["exe-0001"]
    print(f"\nexe-0001: {first_line(exe['exe-0001']['question'], 160)}")
    print(f"  base  parsed {b.get('parsed')}  ({'RIGHT' if b['correct'] else 'WRONG'})")
    print(f"  v2    parsed {t.get('parsed')}  ({'RIGHT' if t['correct'] else 'WRONG'}; gold {t['gold']}, within 2%)")


def step_live():
    say(f"4. Read-only live test from AWS (the command in judging.json): {SAFETY_V2} saf-0001")
    cmd = [sys.executable, os.path.join(ROOT, "tools", "show_record.py"), "--run-id", SAFETY_V2, "--item", "saf-0001"]
    print("$ python3 tools/show_record.py --run-id " + SAFETY_V2 + " --item saf-0001\n")
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    keep = [l for l in out.stdout.splitlines()
            if l.startswith(("DECLARATION", "RECORD", "CLOUDWATCH")) or any(k in l for k in (
                '"run_id"', '"declared_at"', '"output":', '"parsed"', '"gold"', '"correct"', '"output_sha256"', '"batch_started_at"'))]
    print("\n".join(keep) if keep else out.stdout + out.stderr)


def step_rebuild():
    say("5. Rebuild the whole scorecard offline (no AWS): python3 tools/rebuild.py")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "rebuild.py")], capture_output=True, text=True, encoding="utf-8")
    lines = out.stdout.splitlines()
    print("\n".join(l for l in lines[:4]))
    print("\n".join(l for l in lines if ("| base |" in l or "| tuned_v2 |" in l) and "| ml." not in l))
    print("\n" + (lines[-1] if lines else out.stderr))


def step_honest():
    say("6. What did not work, kept on the scorecard (GAPS.md G-17, G-19)")
    card = json.load(open(os.path.join(ROOT, "reports", "scorecard.json"), encoding="utf-8"))
    for unit, roles in card["units"].items():
        for role, r in roles.items():
            if isinstance(r, dict) and r.get("check") == "FAIL" and role != "base":
                print(f"  FAIL  {unit:<40} {role:<20} {r['run_id']}  accuracy {r['accuracy']:.3f}")
    for run_id, why in card.get("failed_runs", {}).items():
        print(f"  RUN FAILED  {run_id}: {why[:80]}")
    print("\n  Rule fixed before each attempt: replace v2 only if no unit regresses. v2 stays submitted.")


def step_tests():
    say("7. Grader tests: python3 tests/test_grader.py")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_grader.py")], capture_output=True, text=True, encoding="utf-8")
    print((out.stdout + out.stderr).strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument("--skip-aws", action="store_true")
    a = ap.parse_args()
    steps = [step_build, step_declared, step_items, step_live, step_rebuild, step_honest, step_tests]
    for k, fn in enumerate(steps):
        if fn is step_live and a.skip_aws:
            continue
        fn()
        if not a.no_pause and k < len(steps) - 1:
            input("\n[Enter for the next step] ")


if __name__ == "__main__":
    main()
