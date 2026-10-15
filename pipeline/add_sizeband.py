import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb, os
D = PROJECT_ROOT + r"\02_PowerBI_Ready\data"
con = duckdb.connect(SCRATCH + r"\star.duckdb")
con.execute("SET memory_limit='3GB'"); con.execute(r"SET temp_directory=SCRATCH + r'\tmp'")
con.execute("SET preserve_insertion_order=false")

con.execute("""
CREATE OR REPLACE TABLE DimActionSize AS
SELECT * FROM (VALUES
 (1,'De-obligation (negative)','a'),
 (2,'Zero dollar','b'),
 (3,'Under $10K','c'),
 (4,'$10K - $250K','d'),
 (5,'$250K - $1M','e'),
 (6,'$1M - $10M','f'),
 (7,'$10M - $100M','g'),
 (8,'$100M and above','h')
) AS t(SizeBandKey, "Action Size Band", "Action Size Sort")
""")

con.execute("""
CREATE OR REPLACE TABLE FactContractTransactions AS
SELECT *, CASE
    WHEN "Obligation" < 0          THEN 1
    WHEN "Obligation" = 0          THEN 2
    WHEN "Obligation" < 10000      THEN 3
    WHEN "Obligation" < 250000     THEN 4
    WHEN "Obligation" < 1000000    THEN 5
    WHEN "Obligation" < 10000000   THEN 6
    WHEN "Obligation" < 100000000  THEN 7
    ELSE 8 END AS SizeBandKey
FROM FactContractTransactions
""")
print(con.execute("""SELECT b."Action Size Band", count(*) n, round(sum(f."Obligation")/1e9,2) obl_bn
                     FROM FactContractTransactions f JOIN DimActionSize b USING(SizeBandKey)
                     GROUP BY 1,b."Action Size Sort" ORDER BY b."Action Size Sort" """).df().to_string(index=False))
for t in ["DimActionSize","FactContractTransactions"]:
    p=os.path.join(D,t+".parquet")
    con.execute(f"COPY {t} TO '{p}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(t, f"{os.path.getsize(p)/1048576:.1f} MB")
