"""Split TeleQnA (MIT, github.com/netop-team/TeleQnA) into a frozen Knowledge test set and a
disjoint training pool.

Test: 500 items stratified by category (seed 7102), options relabelled A-E, gold = letter.
Pool: every other item whose normalised question text does not match a test item.

  python tools/build_knowledge.py --teleqna data/raw/TeleQnA.txt \
      --test-out testsets/knowledge_teleqna.jsonl --pool-out data/train/teleqna_pool.jsonl
"""
import argparse
import collections
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from nlm.common import LETTERS  # noqa: E402

N_TEST = 500
SEED = 7102


def norm(q):
    return re.sub(r"\s+", " ", q.strip().lower())


def load(path):
    raw = json.load(open(path, encoding="utf-8"))
    items = []
    for key, q in raw.items():
        opts = [q[f"option {i}"] for i in range(1, 6) if q.get(f"option {i}") not in (None, "")]
        m = re.match(r"\s*option\s*(\d)", q["answer"], re.IGNORECASE)
        if not m or not (1 <= int(m.group(1)) <= len(opts)):
            continue
        items.append({"id": "tqa-" + key.split()[-1], "category": q["category"], "question": q["question"],
                      "options": opts, "answer": LETTERS[int(m.group(1)) - 1],
                      "explanation": q.get("explanation", "")})
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teleqna", required=True)
    ap.add_argument("--test-out", required=True)
    ap.add_argument("--pool-out", required=True)
    a = ap.parse_args()
    items = load(a.teleqna)
    by_cat = collections.defaultdict(list)
    for it in items:
        by_cat[it["category"]].append(it)
    rng = random.Random(SEED)
    test = []
    for cat in sorted(by_cat):
        k = round(N_TEST * len(by_cat[cat]) / len(items))
        test += rng.sample(by_cat[cat], k)
    test = sorted(test, key=lambda x: int(x["id"].split("-")[1]))[:N_TEST]
    banned = {norm(t["question"]) for t in test}
    pool = [it for it in items if norm(it["question"]) not in banned]
    os.makedirs(os.path.dirname(os.path.abspath(a.pool_out)), exist_ok=True)
    with open(a.test_out, "w", encoding="utf-8", newline="\n") as f:
        for t in test:
            f.write(json.dumps({k: t[k] for k in ("id", "category", "question", "options", "answer")}, ensure_ascii=False) + "\n")
    with open(a.pool_out, "w", encoding="utf-8", newline="\n") as f:
        for p in pool:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"loaded {len(items)}; test {len(test)} {dict(collections.Counter(t['category'] for t in test))}; "
          f"pool {len(pool)} (removed {len(items) - len(pool)} incl. duplicates of test questions)")


if __name__ == "__main__":
    main()
