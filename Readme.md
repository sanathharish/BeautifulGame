Football Analytics Project - Starter
· python

# Football Analytics Project — Starter (Python)

## Overview

This repo scaffolds a reproducible football analytics pipeline:

- **Data sources:** FBref (scraping), optionally other sources later (Understat, Transfermarkt, Opta if licensed)
- **Storage:** SQL Server (development -> production), also local parquet/CSV for intermediate steps
- **Processing / Automation:** Python (requests, BeautifulSoup / pandas), ETL scripts, scheduling via cron or Airflow
- **Analysis / BI:** Power BI (connect to SQL Server, DirectQuery/Import), sample model and visual ideas

---

## Folder structure (suggested)

```
football-analytics/
├─ README.md
├─ requirements.txt
├─ scripts/
│  ├─ fetch_fbref.py        # scraper + basic normalization
│  ├─ etl_to_sql.py         # writes to SQL Server
│  └─ daily_job.sh          # example cron runner
├─ notebooks/
│  ├─ eda_player_stats.ipynb
│  └─ model_feature_engineering.ipynb
├─ sql/
│  ├─ schema.sql
│  └─ seed_data.sql
├─ powerbi/
│  └─ README_powerbi.md
└─ docs/
   └─ project_plan.md
```

---

## Dependencies (requirements.txt)

```
requests
pandas
beautifulsoup4
lxml
pyodbc
sqlalchemy
python-dotenv
schedule
tqdm
pytest
```

## Usage

The `scripts/fetch_fbref.py` script fetches Premier League tables from FBref and writes them to `data/raw` by default.

Examples:

```powershell
# Run with default behaviour (writes per-table CSVs and a single XLSX workbook)
.\.venv\Scripts\python.exe .\scripts\fetch_fbref.py

# Force using Selenium (useful when requests is blocked)
.\.venv\Scripts\python.exe .\scripts\fetch_fbref.py --use-selenium

# Only write CSVs
.\.venv\Scripts\python.exe .\scripts\fetch_fbref.py --format csv

# Only write XLSX
.\.venv\Scripts\python.exe .\scripts\fetch_fbref.py --format xlsx

# Filter to only tables whose id/name contains 'squads'
.\.venv\Scripts\python.exe .\scripts\fetch_fbref.py --tables squads
```

Notes:

- The script uses a requests-first approach with a Selenium fallback when needed.
- Output is written to `data/raw` by default; the `--output` flag can change the path.
