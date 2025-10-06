import pytest
from scripts.fetch_fbref import _flatten_col


def test_flatten_col_string():
    assert _flatten_col(' Club ') == 'club'


def test_flatten_col_tuple():
    assert _flatten_col(('Standard', 'Goals')) == 'standard_goals'


def test_flatten_col_tuple_with_empty():
    assert _flatten_col(('','x')) == 'x'
