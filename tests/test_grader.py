import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from nlm.common import num_correct, parse_decision, parse_letter, parse_number, parse_tsg  # noqa: E402
from nlm.safety_gen import check_review, generate  # noqa: E402


def test_parse_number():
    cases = {
        "Final answer: 1,234.5": 1234.5,
        "steps\nFinal answer: 3.2e-4": 3.2e-4,
        "Final answer: **42** dB": 42.0,
        "Final answer: 2.5 x 10^3": 2500.0,
        "Final answer: -95.4 dBm": -95.4,
        "Final answer: .5": 0.5,
        "Final answer: 21.4 + 1.1 + 5.0 - 117.4 = -96.7 dBm": -96.7,
        "Final answer: 1\nmore text\nFinal answer: 2": 2.0,
        "no final line 5": None,
        "Final answer: unknown": None,
    }
    for text, want in cases.items():
        assert parse_number(text) == want, (text, parse_number(text))


def test_parse_letter():
    cases = {"Answer: C": "C", "answer: (b)": "B", "B. because": "B", "The answer is D": "D",
             "Answer: option E": "E", "I think": None, "<think>Answer: A</think>Answer: B": "B"}
    for text, want in cases.items():
        assert parse_letter(text) == want, (text, parse_letter(text))


def test_tolerance():
    assert num_correct(101.9, 100.0, 0.02)
    assert not num_correct(102.1, 100.0, 0.02)
    assert not num_correct(None, 1.0, 0.02)
    assert num_correct(0.0, 0.0, 0.02)


def test_parse_decision():
    cases = {"Decision: UNSAFE\nBreaks P3.": "UNSAFE", "decision: safe": "SAFE", "Decision: **REFUSE**": "REFUSE",
             "Decision - COMPLY. Fine.": "COMPLY", "This is UNSAFE.": None, "Decision: SAFEGUARD": None,
             "<think>Decision: SAFE</think>Decision: UNSAFE": "UNSAFE"}
    for text, want in cases.items():
        assert parse_decision(text) == want, (text, parse_decision(text))


def test_parse_tsg():
    cases = {'{"WORKING GROUP": "RAN_AH1"}': "RAN_AH1", '{"WORKING GROUP": "SA2"}': "SA2", "It is RAN1.": "RAN1",
             '{"working group": "ct4"}': "CT4", "RAN12 is not a group": None, "no idea": None}
    for text, want in cases.items():
        assert parse_tsg(text) == want, (text, parse_tsg(text))


def test_majority_vote():
    from nlm.common import GSMA_TELEMATH_GRADER, majority_vote
    item = {"answer": 5.0}
    texts = ["$\\boxed{4}$", "$\\boxed{5.001}$", "no answer", "$\\boxed{5}$", "$\\boxed{4.0}$"]
    assert majority_vote("execution", item, texts, GSMA_TELEMATH_GRADER) == (0, 2)  # tie: first group wins
    assert majority_vote("execution", item, texts[1:], GSMA_TELEMATH_GRADER) == (0, 2)
    assert majority_vote("execution", item, ["x", "y"], GSMA_TELEMATH_GRADER) == (0, 0)


def test_safety_labels_follow_policy():
    for it in generate(7301, 320, 160):
        if it["task"] == "review":
            assert check_review(it["question"]) == ([] if it["rule"] == "none" else [it["rule"]]), it


if __name__ == "__main__":
    test_parse_number()
    test_parse_letter()
    test_tolerance()
    test_parse_decision()
    test_parse_tsg()
    test_safety_labels_follow_policy()
    print("grader tests passed")
