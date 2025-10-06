import json
import re
from pathlib import Path
import pandas as pd

MAPPINGS_PATH = Path(__file__).resolve().parents[1] / 'data' / 'mappings' / 'column_mappings.json'


def load_mappings(path: Path = None):
    p = Path(path) if path else MAPPINGS_PATH
    if not p.exists():
        return {'exact': {}, 'regex': []}
    with p.open('r', encoding='utf-8') as fh:
        raw = json.load(fh)
    # compile regex list
    compiled = []
    for pattern, name in raw.get('regex', []):
        compiled.append((re.compile(pattern, flags=re.IGNORECASE), name))
    return {'exact': {k.lower(): v for k, v in raw.get('exact', {}).items()}, 'regex': compiled}


def normalize_columns(df: pd.DataFrame, mappings: dict = None) -> pd.DataFrame:
    if mappings is None:
        mappings = load_mappings()
    df = df.copy()
    new_cols = []
    for c in df.columns:
        name = str(c).strip().lower()
        # flatten spaces and underscores
        name = '_'.join([p for p in name.replace('\n',' ').split() if p])
        # exact
        if name in mappings['exact']:
            new_cols.append(mappings['exact'][name])
            continue
        matched = False
        for pattern, to in mappings['regex']:
            if pattern.search(name):
                new_cols.append(to)
                matched = True
                break
        if not matched:
            new_cols.append(name)
    df.columns = new_cols
    return df


if __name__ == '__main__':
    print('Mappings loaded:', load_mappings())
