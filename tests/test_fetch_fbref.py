import pytest
from scripts.fetch_fbref import _flatten_col
from pathlib import Path


def test_flatten_col_string():
    assert _flatten_col(' Club ') == 'club'


def test_flatten_col_tuple():
    assert _flatten_col(('Standard', 'Goals')) == 'standard_goals'


def test_flatten_col_tuple_with_empty():
    assert _flatten_col(('','x')) == 'x'


def test_find_tables_from_html_fixture(tmp_path):
    from scripts.fetch_fbref import find_tables_from_html, save_outputs
    sample = Path(__file__).parent / 'fixtures' / 'sample_fbref.html'
    html = sample.read_text(encoding='utf-8')
    dfs = find_tables_from_html(html)
    # should find at least the commented squad table and the main table
    assert any('squads' in k or 'main_table' in k for k in dfs.keys())

    out_dir = tmp_path / 'out'
    written = save_outputs(dfs, out_dir, fmt='csv')
    assert written['csv']


def test_clean_headers_basic():
    import pandas as pd
    from scripts.fetch_fbref import clean_headers

    df = pd.DataFrame([[1,2]], columns=[' Club ', ('Std','G')])
    out = clean_headers(df)
    assert 'club' in out.columns
    assert 'std_g' in out.columns


def test_clean_headers_unnamed():
    import pandas as pd
    from scripts.fetch_fbref import clean_headers

    df = pd.DataFrame([[1,2]], columns=['', ''])
    out = clean_headers(df)
    assert 'col_1' in out.columns and 'col_2' in out.columns
