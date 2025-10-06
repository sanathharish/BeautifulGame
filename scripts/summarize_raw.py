"""summarize_raw.py

Scans data/raw for per-table CSVs and writes a summary CSV with:
- table_name (derived from filename)
- file_name
- rows (data rows)
- cols (number of columns)
- sample_headers (first 8 headers joined by ';')

Usage:
    .venv\Scripts\python.exe .\scripts\summarize_raw.py
"""
from pathlib import Path
import csv
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / 'data' / 'raw'
OUT = RAW / 'table_summary.csv'

if not RAW.exists():
    print("No data/raw directory found. Run the fetcher first.")
    sys.exit(1)

rows = []
for p in sorted(RAW.glob('premier_league_*.csv')):
    try:
        with p.open('r', encoding='utf-8', newline='') as fh:
            reader = csv.reader(fh)
            try:
                headers = next(reader)
            except StopIteration:
                headers = []
            # count remaining lines as data rows
            data_rows = sum(1 for _ in reader)
            cols = len(headers)
            sample_headers = ';'.join(headers[:8])
    except Exception as e:
        rows.append({
            'table_name': p.stem,
            'file_name': str(p.name),
            'rows': 'error',
            'cols': 'error',
            'sample_headers': f'error: {e}'
        })
        continue

    rows.append({
        'table_name': p.stem,
        'file_name': str(p.name),
        'rows': data_rows,
        'cols': cols,
        'sample_headers': sample_headers
    })

# write summary
with OUT.open('w', encoding='utf-8', newline='') as outfh:
    w = csv.DictWriter(outfh, fieldnames=['table_name', 'file_name', 'rows', 'cols', 'sample_headers'])
    w.writeheader()
    for r in rows:
        w.writerow(r)

print(f"Wrote summary to: {OUT}")
