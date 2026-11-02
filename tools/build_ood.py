"""Build the out-of-distribution test sets from the official GSMA/ot-full test splits.

These files are NOT committed (TeleMath asks not to redistribute; both stay in the team bucket
and in the git-ignored data/ folder). Their hashes are frozen in testsets/MANIFEST.json.

  python tools/build_ood.py --otfull data/raw/GSMA/ot-full
"""
import argparse
import json
import os
import re
import sys

import pyarrow.parquet as pq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from nlm.common import LETTERS, read_jsonl  # noqa: E402

OUT = os.path.join(ROOT, "data", "testsets")


def norm(q):
    return re.sub(r"\s+", " ", q.strip().lower())


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} items to {os.path.relpath(path, ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--otfull", required=True)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    train = read_jsonl(os.path.join(ROOT, "data", "train", "train.jsonl"))
    train_users = {norm(r["messages"][1]["content"]) for r in train}

    tm = pq.read_table(os.path.join(a.otfull, "telemath", "test-00000-of-00001.parquet")).to_pylist()
    rows = [{"id": f"tm-{i:03d}", "question": r["question"].strip(), "answer": float(r["answer"]),
             "category": r["category"], "difficulty": r.get("difficulty")} for i, r in enumerate(tm)]
    overlap = sum(norm(r["question"]) in train_users for r in rows)
    print(f"telemath: {len(rows)} items; exact overlap with training prompts: {overlap}")
    write(os.path.join(OUT, "execution_telemath_official.jsonl"), rows)

    ob = pq.read_table(os.path.join(a.otfull, "oranbench", "test-00000-of-00001.parquet")).to_pylist()
    rows = [{"id": f"orb-{i:04d}", "question": r["question"].strip(), "options": list(r["choices"]),
             "answer": LETTERS[int(r["answer"])], "difficulty": r.get("difficulty")} for i, r in enumerate(ob)]
    train_q = {norm(m.split("\n\nOptions:")[0].removeprefix("question: ")) for m in train_users}
    overlap = sum(norm(r["question"]) in train_q for r in rows)
    print(f"oranbench: {len(rows)} items; exact question overlap with training items: {overlap}")
    write(os.path.join(OUT, "knowledge_oranbench.jsonl"), rows)


if __name__ == "__main__":
    main()
