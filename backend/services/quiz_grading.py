"""Pure, network-free grading for learner quiz attempts."""
from typing import Any, Tuple


def grade_question(question, submitted: Any) -> bool:
    """True if `submitted` is correct for `question.type` / `question.correct_answer`."""
    correct = question.correct_answer
    t = question.type
    if submitted is None or correct is None:
        return False
    if t == "mcq_single":
        return submitted == correct
    if t == "mcq_multi":
        try:
            return set(submitted) == set(correct)
        except TypeError:
            return False
    if t == "true_false":
        return str(submitted).strip().lower() == str(correct).strip().lower()
    if t == "short_answer":
        return str(submitted).strip().lower() == str(correct).strip().lower()
    return False


def score_quiz(questions, answers: dict) -> Tuple[int, dict]:
    """Return (percentage 0-100, {question_id: bool correct}).

    `answers` keys may be ints or strings (JSON object keys are strings); both are tried.
    """
    total = sum(max(1, q.points) for q in questions) or 1
    earned = 0
    per: dict = {}
    for q in questions:
        submitted = answers.get(q.id, answers.get(str(q.id)))
        ok = grade_question(q, submitted)
        per[q.id] = ok
        if ok:
            earned += max(1, q.points)
    return round(earned / total * 100), per
