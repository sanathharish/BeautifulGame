-- Example DDL for staging and analytics tables

CREATE SCHEMA IF NOT EXISTS analytics;

-- Staging tables are simple and mirror CSV columns; create as needed
-- Example for a generic staging table (adjust columns/types as required)
-- CREATE TABLE dbo.stage_premier_league_stats_squads_standard_for (
--   squad varchar(255),
--   mp int,
--   ...,
--   _etl_run_id uniqueidentifier NULL,
--   _source_file varchar(512) NULL,
--   _loaded_at datetime2 NULL
-- );

-- Analytics table: denormalized wide design (adjust metrics as needed)
CREATE TABLE IF NOT EXISTS analytics.fact_team_season_stats (
  team_id INT NOT NULL,
  season_id INT NOT NULL,
  competition_id INT NULL,
  team_name varchar(255),
  matches_played INT NULL,
  goals INT NULL,
  xg decimal(8,3) NULL,
  xga decimal(8,3) NULL,
  possession_pct decimal(6,3) NULL,
  last_updated datetime2 DEFAULT SYSUTCDATETIME(),
  PRIMARY KEY (team_id, season_id)
);
