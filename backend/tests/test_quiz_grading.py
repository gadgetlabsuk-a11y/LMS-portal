from services.quiz_grading import grade_question, score_quiz


def q(type, correct, points=1):
    class Q: pass
    o = Q(); o.type = type; o.correct_answer = correct; o.points = points; o.id = 1
    return o


def test_mcq_single():
    assert grade_question(q("mcq_single", 2), 2) is True
    assert grade_question(q("mcq_single", 2), 1) is False


def test_mcq_multi_order_insensitive():
    assert grade_question(q("mcq_multi", [0, 2]), [2, 0]) is True
    assert grade_question(q("mcq_multi", [0, 2]), [0]) is False


def test_true_false():
    assert grade_question(q("true_false", "True"), "True") is True
    assert grade_question(q("true_false", "True"), "False") is False


def test_short_answer_normalized():
    assert grade_question(q("short_answer", "Paris"), " paris ") is True
    assert grade_question(q("short_answer", "Paris"), "London") is False


def test_blank_is_incorrect():
    assert grade_question(q("mcq_single", 2), None) is False


def test_score_quiz_percentage_and_pass():
    questions = [q("mcq_single", 0, points=1), q("mcq_single", 1, points=3)]
    questions[0].id, questions[1].id = 10, 11
    # got the 3-point one right, the 1-point one wrong -> 3/4 = 75%
    score, per = score_quiz(questions, {10: 1, 11: 1})
    assert score == 75
    assert per[10] is False and per[11] is True
