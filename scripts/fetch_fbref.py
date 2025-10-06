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
    p = argparse.ArgumentParser(description="Fetch FBref Premier League team stats and save as CSV")
    p.add_argument("--use-selenium", action="store_true", help="Force using Selenium to fetch the page (useful if requests is blocked)")
    p.add_argument("--output", "-o", default=str(OUT_DIR / "premier_league_2024_25_team_stats.csv"), help="Output CSV path")
    return p.parse_args()

args = parse_args()

OUT_PATH = Path(args.output)
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def fetch_url(url, attempts=3, backoff=1.0):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    for i in range(attempts):
        try:
            print(f"Fetching: {url} (attempt {i+1})")
            r = session.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as exc:
            print(f"Request attempt {i+1} failed: {exc}")
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


try:
    if args.use_selenium:
        print("--use-selenium set: using Selenium to fetch the page")
        html = fetch_with_selenium(url)
    else:
        try:
            html = fetch_url(url)
        except Exception as e_req:
            print(f"Requests fetch failed: {e_req}")
            print("Attempting Selenium fallback...")
            html = fetch_with_selenium(url)

    # Use BeautifulSoup to parse
    soup = BeautifulSoup(html, "html.parser")

    # FBref tables are often inside comments. Try several strategies:
    # 1) Find a normal table in the parsed HTML whose id contains 'stats'
    # 2) Fallback to searching HTML comments for the same
    # 3) As a last resort, look for any table whose headers include 'club' or 'squad'
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))

    print(f"Found {len(soup.find_all('table'))} <table> tags in main HTML and {len(comments)} HTML comments to search.")

    df = None

    # Strategy 1: direct table in page
    table = None
    # prefer an exact known id first
    table = soup.find("table", id="stats_standard") or soup.find("table", id="all_stats_standard")
    if not table:
        # look for any table with 'stats' in its id
        for t in soup.find_all("table"):
            tid = t.get('id') or ''
            if 'stats' in tid:
                table = t
                print(f"Found table in main HTML with id='{tid}'")
                break

    # Strategy 2: search inside comments
    if table is None:
        for i, c in enumerate(comments[:50]):
            comment_soup = BeautifulSoup(str(c), "html.parser")
            # first try tables with 'stats' in id
            t = comment_soup.find("table", id=lambda x: x and 'stats' in x)
            if t:
                table = t
                print(f"Found table inside comment #{i} with id='{t.get('id')}'")
                break

    # Strategy 3: fallback — any table with header containing 'club' or 'squad'
    if table is None:
        for i, c in enumerate(comments[:200]):
            comment_soup = BeautifulSoup(str(c), "html.parser")
            for t in comment_soup.find_all("table"):
                headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                if any('club' in h or 'squad' in h or 'team' in h for h in headers):
                    table = t
                    print(f"Found table inside comment #{i} by header match: {headers[:5]}")
                    break
            if table:
                break

    if table is None:
        # Provide helpful diagnostic info instead of a generic error
        raise ValueError(f"Could not find a suitable stats table. Tables found in main HTML: {len(soup.find_all('table'))}, comments checked: {len(comments)}")

    # We'll collect multiple tables and name them based on id or headers
    found_tables = []

    # Add the primary 'table' if found above
    if table is not None:
        found_tables.append(table)

    # Also search the main HTML and comments for other tables of interest (ids containing 'stats', or header matches)
    # This collects additional tables not yet added
    for t in soup.find_all('table'):
        if t not in found_tables:
            tid = (t.get('id') or '').lower()
            if 'stats' in tid or 'squad' in tid or 'standard' in tid:
                found_tables.append(t)

    # Search comments too
    for c in comments:
        comment_soup = BeautifulSoup(str(c), 'html.parser')
        for t in comment_soup.find_all('table'):
            if t not in found_tables:
                headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                if any('club' in h or 'squad' in h or 'team' in h or 'standard' in h for h in headers):
                    found_tables.append(t)

    print(f"Collected {len(found_tables)} candidate tables to export.")

    # Helper to create safe sheet/file names
    def _safe_name(s):
        s = s or ''
        s = s.strip()
        # replace spaces and illegal characters
        for ch in ['/', '\\', ':', '*', '?', '[', ']',']']:
            s = s.replace(ch, '_')
        s = s.replace(' ', '_')
        return s[:31]

    # Normalize/flatten column names (pd.read_html may return MultiIndex columns)
    def _flatten_col(col):
        if isinstance(col, tuple):
            parts = [str(c).strip() for c in col if c is not None and str(c).strip() != '']
            name = "_".join(parts) if parts else ""
        else:
            name = str(col).strip()
        name = name.replace("\n", " ")
        name = "_".join([p for p in name.split() if p])
        return name.lower()

    # Convert all found tables to DataFrames and assign names
    dfs = {}
    for i, t in enumerate(found_tables, start=1):
        tid = t.get('id') or ''
        headers = [th.get_text(strip=True) for th in t.find_all('th')][:3]
        name = tid if tid else "table_{}".format(i)
        name = _safe_name(name)
        try:
            df_i = pd.read_html(str(t))[0]
        except Exception:
            # skip tables that pandas can't parse
            print(f"Skipping table {name}: could not parse with pandas")
            continue
        df_i.columns = [_flatten_col(c) for c in df_i.columns]
        # ensure unique name
        base = name or f"table_{i}"
        final_name = base
        j = 1
        while final_name in dfs:
            final_name = f"{base}_{j}"
            j += 1
        dfs[final_name] = df_i

    if not dfs:
        raise ValueError("No tables parsed into DataFrames.")

    # Save per-table CSVs
    for name, df_i in dfs.items():
        csv_path = OUT_DIR / f"premier_league_{name}.csv"
        df_i.to_csv(csv_path, index=False)
        print(f"Wrote CSV: {csv_path}")

    # Also save a single Excel workbook with one sheet per table + metadata
    try:
        from pandas import ExcelWriter
        from datetime import datetime
        xlsx_path = OUT_DIR / "premier_league_2024_25_team_stats.xlsx"
        with ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            meta = pd.DataFrame({
                "source": [url],
                "fetched_at": [datetime.utcnow().isoformat() + "Z"],
                "tables": [", ".join(dfs.keys())]
            })
            meta.to_excel(writer, sheet_name="metadata", index=False)
            for name, df_i in dfs.items():
                sheet = _safe_name(name)
                df_i.to_excel(writer, sheet_name=sheet, index=False)
        print(f"Wrote workbook: {xlsx_path}")
    except Exception as e:
        print("Could not write Excel workbook:", e)

except Exception as e:
    print("❌ Error:", e)
