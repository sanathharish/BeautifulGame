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


def test_normalize_types():
    import pandas as pd
    from scripts.fetch_fbref import normalize_types

    df = pd.DataFrame({
        'a': ['1', '2', '3'],
        'b': ['x', 'y', 'z'],
        'c': ['1.5', '2.5', '']
    })
    out = normalize_types(df)
    assert pd.api.types.is_numeric_dtype(out['a'])
    assert not pd.api.types.is_numeric_dtype(out['b'])
    # 'c' has 2 numeric values out of 3 so should be numeric
    assert pd.api.types.is_numeric_dtype(out['c'])


def test_header_mappings():
    import pandas as pd
    from scripts.fetch_fbref import clean_headers

    df = pd.DataFrame([[1,2,3,4,5]], columns=['xG', 'npxG', 'Poss%', 'G', 'MP'])
    out = clean_headers(df)
    assert 'xg' in out.columns
    assert 'npxg' in out.columns
    assert 'possession_pct' in out.columns
    assert 'goals' in out.columns
    assert 'matches_played' in out.columns
