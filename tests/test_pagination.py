import pytest
from werkzeug.exceptions import NotFound

from wykoj.blueprints.utils.pagination import Pagination


def test_pages_rounds_up():
    assert Pagination(items=[1], page=1, per_page=10, total=25).pages == 3
    assert Pagination(items=[1], page=1, per_page=10, total=20).pages == 2
    assert Pagination(items=[1], page=1, per_page=10, total=0).pages == 0


def test_empty_page_one_does_not_abort():
    # page 1 is always valid, even with no items/total (e.g. no submissions yet)
    Pagination(items=[], page=1, per_page=10, total=0)


def test_empty_non_first_page_aborts_404():
    with pytest.raises(NotFound):
        Pagination(items=[], page=2, per_page=10, total=25)


def test_iter_pages_single_page_no_ellipsis():
    p = Pagination(items=[1], page=1, per_page=10, total=3)
    assert list(p.iter_pages()) == [1]


def test_iter_pages_all_within_default_edges_no_ellipsis():
    # 10 pages fits entirely within left_edge(2) + left_current(2) + right_current(5) + right_edge(2)
    p = Pagination(items=[1], page=5, per_page=10, total=100)
    assert list(p.iter_pages()) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_iter_pages_inserts_ellipsis_around_gaps():
    p = Pagination(items=[1], page=20, per_page=10, total=300)  # 30 pages, current page 20
    pages = list(p.iter_pages())
    assert pages[0] == 1
    assert pages[1] == 2
    assert None in pages  # gap represented as None
    assert pages[-2] == 29
    assert pages[-1] == 30
    # no two consecutive numbers should have a gap greater than 1 without a None between them
    numbers = [n for n in pages if n is not None]
    assert numbers == sorted(numbers)


def test_iter_pages_custom_thresholds():
    p = Pagination(items=[1], page=1, per_page=10, total=100)  # 10 pages
    pages = list(p.iter_pages(left_edge=1, left_current=0, right_current=0, right_edge=1))
    assert pages == [1, None, 10]
