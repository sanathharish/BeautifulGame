Power BI integration notes

Quick start
1. Use the `analytics.fact_team_season_stats` table as the reporting table in Power BI.
2. For fast development, in Power BI Desktop choose Get Data -> SQL Server -> Import. Enter server and database and select the `analytics` schema.
3. Build visuals and publish to Power BI Service. If your SQL Server is on-premises, configure the On-premises data gateway and set credentials.

Import vs DirectQuery vs Live (SSAS)
- Start with Import for performance and easy development.
- If you need real-time or very large datasets, consider DirectQuery but be mindful of query performance.
- If you need a centralized semantic model or many reports reusing the same DAX, use SSAS Tabular or Power BI Premium datasets and connect via Live Connection.

Scheduling
- Use Power BI Service scheduled refresh (daily/hourly) if using Import mode.
- If using DirectQuery/SSAS, there is no dataset refresh but you must ensure the SSAS model/process is up-to-date.

Security
- Use least-privileged credentials for the gateway.
- Consider row-level security in SSAS/Power BI if required.
