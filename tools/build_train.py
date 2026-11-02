"""Build the LoRA training set (chat JSONL) from sources disjoint from the frozen test sets.

  execution: src/nlm/telemath_gen.py, seed 8202, worked solutions, test questions banned
  knowledge: TeleQnA pool from tools/build_knowledge.py (test items already removed)

Prompts come from nlm.common.messages_for, the same builder the evaluator uses.
Writes data/train/train.jsonl (not committed) and evidence/train_manifest.json (committed).

  python tools/build_train.py --exec-n 6000 [--teleqna-pool data/train/teleqna_pool.jsonl --know-n 6000]
"""
import argparse
import collections
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from nlm.common import GSMA_TELEMATH_GRADER, messages_for, read_jsonl, sha256_file  # noqa: E402
from nlm.safety_gen import generate_train as safety_train  # noqa: E402
from nlm.telemath_gen import generate, question_hash  # noqa: E402

EXEC_TEST = os.path.join(ROOT, "testsets", "execution_telemath_synth.jsonl")
KNOW_TEST = os.path.join(ROOT, "testsets", "knowledge_teleqna.jsonl")
SAFETY_TEST = os.path.join(ROOT, "testsets", "safety_ran.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exec-n", type=int, default=6000)
    ap.add_argument("--exec-seed", type=int, default=8202)
    ap.add_argument("--teleqna-pool", default="")
    ap.add_argument("--know-n", type=int, default=0)
    ap.add_argument("--gsma-n", type=int, default=0, help="extra calculation problems in the GSMA TeleMath prompt and \\boxed{} format")
    ap.add_argument("--gsma-seed", type=int, default=8212)
    ap.add_argument("--safety-review-n", type=int, default=0)
    ap.add_argument("--safety-request-n", type=int, default=0)
    ap.add_argument("--safety-seed", type=int, default=8302)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "train", "train.jsonl"))
    ap.add_argument("--manifest", default=os.path.join(ROOT, "evidence", "train_manifest.json"))
    a = ap.parse_args()

    rows = []
    banned = frozenset(question_hash(t["question"]) for t in read_jsonl(EXEC_TEST))
    for it in generate(a.exec_seed, a.exec_n, "trn-exe", banned, with_work=True):
        rows.append({"source": "telemath_gen", "id": it["id"],
                     "messages": messages_for("execution", it) + [{"role": "assistant", "content": it["work"]}]})
    seen = {question_hash(it["question"]) for it in generate(a.exec_seed, a.exec_n, "trn-exe", banned)}
    if a.gsma_n:  # same generator, other seed; reply ends the GSMA way: unit stated, then only the number boxed
        n = 0
        for it in generate(a.gsma_seed, a.gsma_n * 2, "trn-gsm", banned, with_work=True):
            if n == a.gsma_n or question_hash(it["question"]) in seen:
                continue
            work = it["work"].rsplit("\nFinal answer:", 1)[0]
            value = it["work"].rsplit("Final answer:", 1)[1].strip()
            reply = f"{work}\nThe answer is in {it['unit']}.\n$\\boxed{{{value}}}$"
            rows.append({"source": "telemath_gen_gsma_format", "id": it["id"],
                         "messages": messages_for("execution", it, GSMA_TELEMATH_GRADER) + [{"role": "assistant", "content": reply}]})
            n += 1
    if a.safety_review_n or a.safety_request_n:
        banned_safety = frozenset(t["question"] for t in read_jsonl(SAFETY_TEST))
        for k, it in enumerate(safety_train(a.safety_seed, a.safety_review_n, a.safety_request_n, banned_safety)):
            rows.append({"source": f"safety_{it['task']}", "id": f"trn-saf-{k:05d}",
                         "messages": messages_for("safety", it) + [{"role": "assistant", "content": it["reply"]}]})
    if a.teleqna_pool:
        test_q = {t["question"].strip().lower() for t in read_jsonl(KNOW_TEST)}
        pool = [p for p in read_jsonl(a.teleqna_pool) if p["question"].strip().lower() not in test_q]
        random.Random(8203).shuffle(pool)
        for it in pool[: a.know_n or len(pool)]:
            rows.append({"source": "teleqna", "id": it["id"],
                         "messages": messages_for("knowledge", it) + [{"role": "assistant", "content": f"Answer: {it['answer']}"}]})
    random.Random(8204).shuffle(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rel_out = os.path.relpath(a.out, ROOT).replace("\\", "/")
    manifest = {"file": f"{rel_out} (not committed; s3://bb26-p-team07-data-041915167631-use2/nlm-track1/train/<run_id>/train.jsonl)",
                "sha256": sha256_file(a.out), "rows": len(rows),
                "by_source": dict(collections.Counter(r["source"] for r in rows)),
                "exec_seed": a.exec_seed, "exec_test_questions_banned": len(banned),
                "knowledge_test_items_excluded": os.path.exists(KNOW_TEST),
                "build": " ".join(["python tools/build_train.py"] + sys.argv[1:])}
    if a.gsma_n:
        manifest["gsma_seed"] = a.gsma_seed
    if a.safety_review_n or a.safety_request_n:
        manifest.update(safety_seed=a.safety_seed, safety_test_questions_banned=True,
                        safety_request_templates="TRAIN_* templates only (test topics never trained on)")
    with open(a.manifest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
