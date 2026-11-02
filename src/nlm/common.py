"""Prompt and grading contract shared by baseline, tuned and adapter runs.

The same prompt builders and the same rule-based parsers are used for every model, so
base and tuned scores are comparable. No LLM is involved in grading.
"""
import hashlib
import json
import math
import re

GRADER_ID = "rule-based-parser-v1"
LETTERS = "ABCDE"

KNOW_SYS = (
    "You are a telecommunications expert. Answer the multiple-choice question. "
    "Reply with exactly one line of the form 'Answer: <letter>' where <letter> is the "
    "letter of the single correct option."
)
EXEC_SYS = (
    "You are a telecom mathematical reasoning assistant. Solve the numerical problem "
    "using a short, accurate sequence of calculation steps and correct unit conversions. "
    "Show the formula and substitution. Finish with exactly one line of the form "
    "Final answer: <number>. The last line must contain only that label and a numerical "
    "value in the requested units; scientific notation is permitted."
)

# Execution tolerance: primary relative tolerance, plus a looser secondary metric.
EXEC_REL_TOL = 0.02
EXEC_REL_TOL_LOOSE = 0.05

# GSMA official TeleMath protocol, ported verbatim from github.com/gsma-labs/evals (MIT),
# commit 708f1c5498793536824eae9919ae003f13c910ea, src/evals/telemath/telemath.py.
GSMA_TELEMATH_GRADER = "gsma-evals-telemath@708f1c5"
GSMA_TELEMATH_SYS = r"""You are an expert problem solver. Your task is to solve numerical exercises by following these guidelines:
1.  **Understand the Goal:** Clearly identify what the problem is asking you to find, paying close attention to the required units for the final answer.
2.  **Reason Step-by-Step:** Provide a clear, sequential reasoning process. Explain the formulas, principles, or logic used in each step. Show intermediate calculations if they clarify your thought process. The detailed structure of your sub-steps is up to you, as long as the reasoning is sound and easy to follow.
3.  **Unit Management:**
    *   Track units throughout your calculations.
    *   **Crucially, ensure your final numerical answer is converted to the specific units requested in the problem statement.** If intermediate calculations result in a different unit, perform a final conversion step.
    *   State the unit of the final answer clearly in your explanatory text *before* the boxed answer.
4.  **Final Numerical Answer Format:**
    *   The final answer must be a single numerical value (integer or float).
    *   Present this numerical value exclusively within the `\$\boxed{{...}}\$` format.
    *   **CRITICAL:** The `\$\boxed{{...}}\$` block must contain *only* the number. No text, no units, no labels (e.g., NOT `\$\boxed{{Result: 50}}\$` or `\$\boxed{{50 \text{{ mA}}}}\$`, but `\$\boxed{{50}}\$`)."""
_BOXED = re.compile(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}")
_WS = re.compile(r"\n\s*")


def parse_boxed(text):
    """gsma-labs/evals parse_boxed_answer: last \\boxed{...}, whitespace removed."""
    matches = _BOXED.findall(text or "")
    if not matches:
        return ""
    return _WS.sub("", matches[-1].strip()).lstrip(":").rstrip("./")


def gsma_telemath_correct(parsed, target):
    """gsma-labs/evals telemath_scorer: isclose(rel_tol=0.01, abs_tol=0.01), else string equality."""
    try:
        return math.isclose(float(parsed), float(target), rel_tol=0.01, abs_tol=0.01)
    except (ValueError, TypeError):
        return parsed == str(target)


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------- prompts ----------

def know_user(item):
    opts = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(item["options"]))
    return f"Question: {item['question']}\n\nOptions:\n{opts}"


def exec_user(item):
    return item["question"] + (f" Give the answer in {item['unit']}." if item.get("unit") else "")


def messages_for(unit, item, grader=GRADER_ID):
    if grader == GSMA_TELEMATH_GRADER:  # GSMA protocol: its system prompt, the bare question
        return [{"role": "system", "content": GSMA_TELEMATH_SYS}, {"role": "user", "content": item["question"]}]
    if unit == "knowledge":
        return [{"role": "system", "content": KNOW_SYS}, {"role": "user", "content": know_user(item)}]
    if unit == "execution":
        return [{"role": "system", "content": EXEC_SYS}, {"role": "user", "content": exec_user(item)}]
    raise ValueError(unit)


# ---------- parsers ----------

_ANS = re.compile(r"answer\s*[:\-]?\s*(?:is\s*)?(?:option\s*)?\(?([A-E])\b", re.IGNORECASE)
_LEAD = re.compile(r"^\s*\(?([A-E])[\).:]?(?:\s|$)")
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def parse_letter(text):
    t = _THINK.sub("", text)
    m = _ANS.search(t)
    if m:
        return m.group(1).upper()
    m = _LEAD.match(t)
    return m.group(1).upper() if m else None


NUM = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?(?:[eE][-+]?\d+)?(?:\s*(?:x|\*|×)\s*10\^\s*[-+]?\d+)?"
_FINAL_LINE = re.compile(r"final answer\s*[:=]?(.*)", re.IGNORECASE)
_FIRST_NUM = re.compile(r"\s*\**\s*(" + NUM + r")")


def _to_float(s):
    s = s.replace(",", "").replace(" ", "")
    m = re.match(r"^([-+]?[\d.]+(?:[eE][-+]?\d+)?)(?:[x*×]10\^([-+]?\d+))?$", s)
    if not m or m.group(1) in ("", ".", "+", "-"):
        return None
    try:
        v = float(m.group(1)) * (10 ** int(m.group(2)) if m.group(2) else 1)
    except (ValueError, OverflowError):
        return None
    return v if math.isfinite(v) else None


def parse_number(text):
    """Number on the last 'Final answer:' line; if that line is an equation, the value after the last '='."""
    lines = _FINAL_LINE.findall(_THINK.sub("", text))
    if not lines:
        return None
    tail = lines[-1].rsplit("=", 1)[-1]
    m = _FIRST_NUM.match(tail)
    return _to_float(m.group(1)) if m and re.search(r"\d", m.group(1)) else None


def num_correct(pred, gold, rel_tol):
    if pred is None:
        return False
    if gold == 0.0:
        return abs(pred) <= 1e-9
    return math.isclose(pred, gold, rel_tol=rel_tol, abs_tol=0.0)


def grade(unit, item, output, grader=GRADER_ID):
    """Return the graded fields for one item. Pure function of (item, output, grader)."""
    if grader == GSMA_TELEMATH_GRADER:
        pred = parse_boxed(output)
        return {"parsed": pred or None, "gold": item["answer"], "correct": gsma_telemath_correct(pred, item["answer"])}
    if unit == "knowledge":
        pred = parse_letter(output)
        return {"parsed": pred, "gold": item["answer"], "correct": pred == item["answer"]}
    pred = parse_number(output)
    return {"parsed": pred, "gold": item["answer"],
            "correct": num_correct(pred, item["answer"], EXEC_REL_TOL),
            "correct_loose": num_correct(pred, item["answer"], EXEC_REL_TOL_LOOSE)}


def summarise(unit, records):
    n = len(records)
    out = {"n": n, "accuracy": sum(r["correct"] for r in records) / n if n else 0.0,
           "unparsed": sum(r["parsed"] is None for r in records)}
    if unit == "execution":
        out["accuracy_loose_5pct"] = sum(r.get("correct_loose", False) for r in records) / n if n else 0.0
    lat = sorted(r["latency_s"] for r in records if "latency_s" in r)
    if lat:
        out["latency_p50_s"] = lat[len(lat) // 2]
        out["latency_p95_s"] = lat[min(len(lat) - 1, int(len(lat) * 0.95))]
    return out
