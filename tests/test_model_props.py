from wykoj.models import ContestTaskPoints, Task


def test_contest_task_points_round_trip():
    ctp = ContestTaskPoints()
    ctp.points = [1, 2.5, 0]
    assert ctp.points == [1, 2.5, 0]


def test_contest_task_points_collapses_integral_floats_to_int():
    ctp = ContestTaskPoints()
    ctp.points = [3.0]
    assert ctp.points == [3]
    assert isinstance(ctp.points[0], int)


def test_contest_task_points_total_points_sums_subtasks():
    ctp = ContestTaskPoints()
    ctp.points = [1, 2.5, 3]
    assert ctp.total_points == 6.5


def test_ogp_preview_extracts_first_paragraph_only():
    task = Task(content="<p>First paragraph.</p><p>Second paragraph, ignored.</p>")
    assert task.ogp_preview == "First paragraph."


def test_ogp_preview_strips_katex_delimiters():
    task = Task(content=r"<p>Let $x$ and $$y$$ be integers.</p>")
    assert task.ogp_preview == "Let x and y be integers."


def test_ogp_preview_unescapes_literal_dollar_sign():
    task = Task(content=r"<p>Costs \$5 in total.</p>")
    assert task.ogp_preview == "Costs $5 in total."


def test_ogp_preview_collapses_whitespace():
    task = Task(content="<p>Line one\n   Line two\n\tLine three</p>")
    assert task.ogp_preview == "Line one Line two Line three"
