"""load_to_sql.py

Simple ETL script to load CSVs from data/raw into SQL Server staging tables
and then upsert into an analytics table. This is a minimal, opinionated loader
intended as a starting point.

Usage:
  .venv\Scripts\python.exe .\scripts\load_to_sql.py --connection "DRIVER=...;SERVER=...;DATABASE=...;UID=...;PWD=..." 

It expects:
- data/raw/premier_league_*.csv files
- staging schema: dbo.stage_<filename_stem>
- analytics schema/table: analytics.fact_team_season_stats (DDL in sql/ddl.sql)

NOTE: This script uses pyodbc and pandas. For large files prefer BULK INSERT.
"""
import argparse
from pathlib import Path
import pandas as pd
import pyodbc
import sqlalchemy
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / 'data' / 'raw'


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--connection', required=True, help='pyodbc connection string')
    p.add_argument('--truncate-staging', action='store_true', help='Truncate staging tables before load')
    return p.parse_args()


def get_engine(conn_str):
    # Expect a pyodbc connection string; convert to sqlalchemy URL
    return sqlalchemy.create_engine(f"mssql+pyodbc:///?odbc_connect={conn_str}")


def load_csv_to_stage(engine, csv_path: Path, stage_table: str, truncate=False):
    df = pd.read_csv(csv_path)
    with engine.begin() as conn:
        if truncate:
            conn.execute(text(f"TRUNCATE TABLE {stage_table}"))
        # write to staging; if exists append
        df.to_sql(stage_table.split('.')[-1], con=conn, schema='dbo', if_exists='append', index=False)
    return len(df)


def upsert_to_analytics(engine):
    # Placeholder: you should implement MERGE logic here specific to your analytics schema.
    with engine.begin() as conn:
        # Example: simple copy from a canonical staging to analytics (replace with MERGE)
        conn.execute(text("-- TODO: implement MERGE from staging to analytics"))


if __name__ == '__main__':
    args = parse_args()
    engine = get_engine(args.connection)
    csvs = sorted(RAW.glob('premier_league_*.csv'))
    for csv in csvs:
        stem = csv.stem
        stage_table = f"dbo.stage_{stem}"
        print(f"Loading {csv} -> {stage_table}")
        rows = load_csv_to_stage(engine, csv, stage_table, truncate=args.truncate_staging)
        print(f"Loaded {rows} rows into {stage_table}")
    upsert_to_analytics(engine)
    print('ETL done')
