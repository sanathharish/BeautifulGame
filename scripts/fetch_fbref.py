"""
fetch_fbref.py
---------------
Scrapes Premier League 2024–25 team statistics from FBref
using Selenium and saves them as a CSV file.
Handles tables embedded inside HTML comments.
"""

import argparse
import requests
import pandas as pd
from pathlib import Path
import time
from bs4 import BeautifulSoup, Comment
from io import StringIO
import re
import logging

# configure basic logging for script and tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------
# Output folder (use repository root so we always write to the single top-level data/raw)
# ----------------------------
# Determine project root relative to this script file (two levels up from this file is repository root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------
# FBref URL
# ----------------------------
url = "https://fbref.com/en/comps/9/Premier-League-Stats"

def parse_args():
    p = argparse.ArgumentParser(description="Fetch FBref Premier League team stats and save as CSV/XLSX")
    p.add_argument("--use-selenium", action="store_true", help="Force using Selenium to fetch the page (useful if requests is blocked)")
    p.add_argument("--output", "-o", default=str(OUT_DIR / "premier_league_2024_25_team_stats.csv"), help="Output path (for CSV or XLSX)")
    p.add_argument("--format", choices=["csv", "xlsx", "both"], default="both", help="Output format: csv, xlsx, or both")
    p.add_argument("--tables", help="Comma-separated list of table id/name substrings to export (e.g. 'squads,standard')")
    p.add_argument("--no-clean", action="store_true", help="Disable header cleaning before writing outputs")
    p.add_argument("--no-types", action="store_true", help="Disable automatic column type normalization (numbers) before writing outputs")
    return p


OUT_PATH = None

def fetch_url(url, attempts=3, backoff=1.0):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    for i in range(attempts):
        try:
            logger.info("Fetching: %s (attempt %d)", url, i + 1)
            r = session.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as exc:
            logger.warning("Request attempt %d failed: %s", i + 1, exc)
            time.sleep(backoff * (2 ** i))
    raise RuntimeError(f"Failed to fetch {url} after {attempts} attempts")

def fetch_with_selenium(url, wait=5):
    """Dynamically import selenium and use a headless browser to fetch the page.
    Raises ImportError if selenium or webdriver-manager are not available.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:
        raise ImportError("Selenium fallback requires 'selenium' and 'webdriver-manager' packages. Install them with: pip install selenium webdriver-manager") from e

    options = Options()
    # run headless but try to appear as a regular browser
    options.add_argument('--headless=new')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(url)
        time.sleep(wait)
        return driver.page_source
    finally:
        driver.quit()


def _safe_name(s):
    s = s or ''
    s = s.strip()
    for ch in ['/', '\\', ':', '*', '?', '[', ']',']']:
        s = s.replace(ch, '_')
    s = s.replace(' ', '_')
    return s[:31]


def _flatten_col(col):
    if isinstance(col, tuple):
        parts = [str(c).strip() for c in col if c is not None and str(c).strip() != '']
        name = "_".join(parts) if parts else ""
    else:
        name = str(col).strip()
    name = name.replace("\n", " ")
    name = "_".join([p for p in name.split() if p])
    return name.lower()


def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names: strip, replace whitespace/newlines, lower-case, and collapse repeated separators.

    Also remove columns that are completely unnamed like '' by replacing them with a placeholder.
    Returns a new DataFrame with cleaned columns (does not modify input).
    """
    df = df.copy()
    new_cols = []

    def _map_name(name: str) -> str:
        # map common metric names to canonical forms
        # handle npxg before xg
        if 'npx' in name or name.startswith('npxg'):
            return 'npxg'
        if name.startswith('xg') or name == 'xg' or re.search(r'(^|_)xg($|_)', name):
            return 'xg'
        if name.startswith('xa') or name == 'xa' or re.search(r'(^|_)xa($|_)', name):
            return 'xa'
        if 'poss' in name or 'possession' in name or name.endswith('%') or name.endswith('_pct'):
            return 'possession_pct'
        # goals: common abbreviations
        if name in ('g', 'goals', 'gls') or name.endswith('_goals'):
            return 'goals'
        if name in ('mp', 'matches', 'appearances'):
            return 'matches_played'
        return name

    for c in df.columns:
        name = _flatten_col(c)
        if not name:
            # assign a placeholder for unnamed columns
            i = len(new_cols) + 1
            name = f"col_{i}"
        # collapse multiple underscores
        while '__' in name:
            name = name.replace('__', '_')
        # apply mapping
        name = _map_name(name)
        new_cols.append(name)
    df.columns = new_cols
    return df


def find_tables_from_html(html):
    """Return a dict of safe_name -> BeautifulSoup table elements found in the page (search main HTML and comments)."""
    soup = BeautifulSoup(html, "html.parser")
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    logger.info("Found %d <table> tags in main HTML and %d HTML comments to search.", len(soup.find_all('table')), len(comments))

    table = None
    table = soup.find("table", id="stats_standard") or soup.find("table", id="all_stats_standard")
    if not table:
        for t in soup.find_all("table"):
            tid = t.get('id') or ''
            if 'stats' in tid:
                table = t
                logger.info("Found table in main HTML with id='%s'", tid)
                break

    if table is None:
        for i, c in enumerate(comments[:50]):
            comment_soup = BeautifulSoup(str(c), "html.parser")
            t = comment_soup.find("table", id=lambda x: x and 'stats' in x)
            if t:
                table = t
                logger.info("Found table inside comment #%d with id='%s'", i, t.get('id'))
                break

    if table is None:
        for i, c in enumerate(comments[:200]):
            comment_soup = BeautifulSoup(str(c), "html.parser")
            for t in comment_soup.find_all("table"):
                headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                if any('club' in h or 'squad' in h or 'team' in h for h in headers):
                    table = t
                    logger.info("Found table inside comment #%d by header match: %s", i, headers[:5])
                    break
            if table:
                break

    found_tables = []
    if table is not None:
        found_tables.append(table)

    for t in soup.find_all('table'):
        if t not in found_tables:
            tid = (t.get('id') or '').lower()
            if 'stats' in tid or 'squad' in tid or 'standard' in tid:
                found_tables.append(t)

    for c in comments:
        comment_soup = BeautifulSoup(str(c), 'html.parser')
        for t in comment_soup.find_all('table'):
            if t not in found_tables:
                headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                if any('club' in h or 'squad' in h or 'team' in h or 'standard' in h for h in headers):
                    found_tables.append(t)

    logger.info("Collected %d candidate tables to export.", len(found_tables))

    dfs = {}
    for i, t in enumerate(found_tables, start=1):
        tid = t.get('id') or ''
        name = tid if tid else f"table_{i}"
        name = _safe_name(name)
        try:
            # Wrap literal HTML in a StringIO to avoid pandas future warning
            df_i = pd.read_html(StringIO(str(t)))[0]
        except Exception:
            logger.warning("Skipping table %s: could not parse with pandas", name)
            continue
        df_i.columns = [_flatten_col(c) for c in df_i.columns]
        base = name or f"table_{i}"
        final_name = base
        j = 1
        while final_name in dfs:
            final_name = f"{base}_{j}"
            j += 1
        dfs[final_name] = df_i

    return dfs


def normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert numeric-like columns to numeric dtype (coerce errors). Returns a copy."""
    df = df.copy()
    for col in df.columns:
        # try to coerce to numeric; leave as-is if many NaNs
        coerced = pd.to_numeric(df[col], errors='coerce')
        # adopt if at least half of values converted to numbers
        non_na = coerced.notna().sum()
        if non_na >= max(1, len(df) // 2):
            df[col] = coerced
    return df


def save_outputs(dfs, out_dir: Path, fmt: str = "both", clean: bool = True, normalize_types_flag: bool = True):
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {
        'csv': [],
        'xlsx': None
    }
    if fmt in ("csv", "both"):
        for name, df_i in dfs.items():
            if clean:
                df_to_write = clean_headers(df_i)
            else:
                df_to_write = df_i
            if normalize_types_flag:
                df_to_write = normalize_types(df_to_write)
            csv_path = out_dir / f"premier_league_{name}.csv"
            df_to_write.to_csv(csv_path, index=False)
            logger.info("Wrote CSV: %s", csv_path)
            written['csv'].append(str(csv_path))

    if fmt in ("xlsx", "both") and dfs:
        try:
            from pandas import ExcelWriter
            from datetime import datetime
            xlsx_path = out_dir / "premier_league_2024_25_team_stats.xlsx"
            with ExcelWriter(xlsx_path, engine="openpyxl") as writer:
                meta = pd.DataFrame({
                    "source": [url],
                    "fetched_at": [datetime.utcnow().isoformat() + "Z"],
                    "tables": [", ".join(dfs.keys())]
                })
                meta.to_excel(writer, sheet_name="metadata", index=False)
                for name, df_i in dfs.items():
                    sheet = _safe_name(name)
                    if clean:
                        df_to_write = clean_headers(df_i)
                    else:
                        df_to_write = df_i
                    if normalize_types_flag:
                        df_to_write = normalize_types(df_to_write)
                    df_to_write.to_excel(writer, sheet_name=sheet, index=False)
            logger.info("Wrote workbook: %s", xlsx_path)
            written['xlsx'] = str(xlsx_path)
        except Exception as e:
            logger.exception("Could not write Excel workbook: %s", e)

    return written


def main(argv=None):
    p = parse_args()
    args = p.parse_args(argv)

    global OUT_PATH
    OUT_PATH = Path(args.output)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        if args.use_selenium:
            logger.info("--use-selenium set: using Selenium to fetch the page")
            html = fetch_with_selenium(url)
        else:
            try:
                html = fetch_url(url)
            except Exception as e_req:
                logger.warning("Requests fetch failed: %s", e_req)
                logger.info("Attempting Selenium fallback...")
                html = fetch_with_selenium(url)

        dfs = find_tables_from_html(html)

        # apply table filters if requested
        if args.tables:
            wanted = [w.strip().lower() for w in args.tables.split(',') if w.strip()]
            dfs = {k: v for k, v in dfs.items() if any(w in k.lower() for w in wanted)}
            logger.info("Filtered tables to %d items", len(dfs))

        if not dfs:
            raise ValueError("No tables parsed into DataFrames after filtering.")

        out = save_outputs(dfs, OUT_PATH.parent, fmt=args.format, clean=(not args.no_clean), normalize_types_flag=(not args.no_types))
        logger.info("Export complete: %s", out)
        return out
    except Exception as e:
        logger.exception("❌ Error: %s", e)
        raise


if __name__ == '__main__':
    main()
