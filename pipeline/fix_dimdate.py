import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb, os
D = PROJECT_ROOT + r"\02_PowerBI_Ready\data"
con = duckdb.connect(SCRATCH + r"\star.duckdb")
con.execute("SET memory_limit='2GB'"); con.execute(r"SET temp_directory=SCRATCH + r'\tmp'")
con.execute("""
CREATE OR REPLACE TABLE DimDate AS
WITH d AS (SELECT unnest(generate_series(DATE '2024-10-01', DATE '2025-09-30', INTERVAL 1 DAY))::DATE AS dt),
     f AS (SELECT dt, ((month(dt) + 2) % 12) + 1 AS fmi FROM d)
SELECT
  CAST(strftime(dt,'%Y%m%d') AS INTEGER)                       AS DateKey,
  dt                                                           AS "Date",
  CASE WHEN month(dt) >= 10 THEN year(dt)+1 ELSE year(dt) END  AS "Fiscal Year",
  'FY' || CAST(CASE WHEN month(dt) >= 10 THEN year(dt)+1 ELSE year(dt) END AS VARCHAR) AS "Fiscal Year Label",
  fmi                                                          AS "Fiscal Month Number",
  'Q' || CAST(CAST(floor((fmi - 1) / 3.0) AS INTEGER) + 1 AS VARCHAR) AS "Fiscal Quarter",
  year(dt)                                                     AS "Calendar Year",
  month(dt)                                                    AS "Month Number",
  strftime(dt,'%b')                                            AS "Month Short",
  strftime(dt,'%B')                                            AS "Month Name",
  strftime(dt,'%b %Y')                                         AS "Month Year",
  CAST(strftime(dt,'%Y%m') AS INTEGER)                         AS "Month Year Sort",
  day(dt)                                                      AS "Day Of Month",
  strftime(dt,'%a')                                            AS "Day Of Week Short",
  isodow(dt)                                                   AS "Day Of Week Number",
  CASE WHEN isodow(dt) >= 6 THEN TRUE ELSE FALSE END           AS "Is Weekend"
FROM f
""")
print(con.execute("""SELECT "Fiscal Quarter", min("Date") first_day, max("Date") last_day, count(*) n_days
                     FROM DimDate GROUP BY 1 ORDER BY 1""").df().to_string(index=False))
con.execute(f"COPY DimDate TO '{os.path.join(D,'DimDate.parquet')}' (FORMAT PARQUET, COMPRESSION ZSTD)")
print("DimDate re-exported")
# offers distribution
con.execute(f"CREATE OR REPLACE VIEW F AS SELECT * FROM read_parquet('{os.path.join(D,'FactContractTransactions.parquet')}')")
print(con.execute("""
SELECT CASE WHEN "Offers Received" IS NULL THEN 'null'
            WHEN "Offers Received" = 1 THEN '1'
            WHEN "Offers Received" BETWEEN 2 AND 5 THEN '2-5'
            WHEN "Offers Received" BETWEEN 6 AND 20 THEN '6-20'
            WHEN "Offers Received" BETWEEN 21 AND 100 THEN '21-100'
            WHEN "Offers Received" BETWEEN 101 AND 1000 THEN '101-1000'
            ELSE '>1000' END bucket,
       count(*) n, max("Offers Received") max_offers
FROM F GROUP BY 1 ORDER BY n DESC""").df().to_string(index=False))
print()
print(con.execute("""SELECT median("Offers Received") med, avg("Offers Received") avg_all,
       avg("Offers Received") FILTER (WHERE "Offers Received" <= 100) avg_le100
FROM F WHERE "Offers Received" IS NOT NULL""").df().to_string(index=False))
