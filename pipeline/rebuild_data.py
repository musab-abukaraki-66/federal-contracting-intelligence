"""Project 06 - rebuild the Power BI-facing data files.

Changes vs the first build:
  1. DimAward drops the stored 'USAspending Link' column (5.83 M unique 60-char URLs).
     The URL is deterministic from 'Award Unique Key' and is rebuilt as a DAX measure.
  2. The two large tables are written as MULTIPLE parquet files so the semantic model can
     use one partition per file and refresh them in parallel instead of single-threaded.
  3. CSV copies of the fact table are written to a scratch area for the ingestion benchmark
     (they are NOT part of the deliverable unless the benchmark says CSV wins).

Source of truth stays <SCRATCH>\\star.duckdb, built and integrity-checked earlier.
"""
import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")

import duckdb, os, shutil, time

DATA  = PROJECT_ROOT + r"\02_PowerBI_Ready\data"
BENCH = SCRATCH + r"\bench"
TMP   = SCRATCH + r"\tmp"
PARTS = 8          # fact partitions
AWARD_PARTS = 4    # DimAward partitions

con = duckdb.connect(SCRATCH + r"\star.duckdb")
con.execute("SET memory_limit='3GB'")
con.execute(f"SET temp_directory='{TMP}'")
con.execute("SET preserve_insertion_order=false")
con.execute("SET threads=4")

def cardinality_report():
    print("DimAward column cardinality (drives VertiPaq dictionary cost):")
    cols = ["Award Unique Key", "Award PIID", "Parent Award PIID", "Award or IDV",
            "USAspending Link"]
    have = [r[0] for r in con.execute("DESCRIBE DimAward").fetchall()]
    for c in cols:
        if c not in have:
            continue
        n, avg = con.execute(
            f'SELECT count(DISTINCT "{c}"), avg(length(CAST("{c}" AS VARCHAR))) FROM DimAward'
        ).fetchone()
        print(f"  {c:<22} distinct={n:>10,}  avg_len={avg or 0:5.1f}  "
              f"~{(n * (avg or 0))/1048576:6.1f} MB of raw dictionary text")

cardinality_report()

# ---------------------------------------------------------------- DimAward, slimmed
print("\nrebuilding DimAward without the derived URL column")
con.execute("""
CREATE OR REPLACE TABLE DimAwardSlim AS
SELECT AwardKey,
       "Award Unique Key",
       "Award PIID",
       "Parent Award PIID",
       "Award or IDV",
       "Award Current Value",
       "Award Potential Value",
       "Performance Start",
       "Performance End"
FROM DimAward
""")
print("  columns kept:", [r[0] for r in con.execute("DESCRIBE DimAwardSlim").fetchall()])

# ---------------------------------------------------------------- partitioned writers
def write_parts(table, folder, parts, order_col):
    out = os.path.join(DATA, folder)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    per = -(-total // parts)
    t0 = time.time()
    for i in range(parts):
        path = os.path.join(out, f"part_{i+1:02d}.parquet")
        con.execute(f"""
            COPY (SELECT * FROM {table} WHERE {order_col} > {i*per} AND {order_col} <= {(i+1)*per})
            TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 200000)
        """)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    got = con.execute(f"SELECT count(*) FROM read_parquet('{out}\\*.parquet')").fetchone()[0]
    print(f"  {folder}: {parts} files, {got:,} rows (source {total:,}), "
          f"{size/1048576:.1f} MB, {time.time()-t0:.0f}s")
    assert got == total, f"row count mismatch for {table}"
    return out

# fact needs a monotonic key to slice on - add a row id
print("\nwriting partitioned parquet")
con.execute("""
CREATE OR REPLACE TABLE FactPart AS
SELECT *, row_number() OVER () AS _rn FROM FactContractTransactions
""")
con.execute("""
CREATE OR REPLACE VIEW FactOut AS
SELECT DateKey, AgencyKey, FundingAgencyKey, RecipientKey, AwardKey, NaicsKey, PscKey,
       CompetitionKey, ContractTypeKey, ActionTypeKey, PlaceKey, SizeBandKey,
       "Obligation", "Offers Received", _rn
FROM FactPart
""")
con.execute('CREATE OR REPLACE VIEW FactOutClean AS SELECT * EXCLUDE (_rn) FROM FactOut')

def write_parts_expr(view, folder, parts, key_col, total):
    out = os.path.join(DATA, folder)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    per = -(-total // parts)
    t0 = time.time()
    for i in range(parts):
        path = os.path.join(out, f"part_{i+1:02d}.parquet")
        con.execute(f"""
            COPY (SELECT * EXCLUDE ({key_col}) FROM {view}
                  WHERE {key_col} > {i*per} AND {key_col} <= {(i+1)*per})
            TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 200000)
        """)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    got = con.execute(f"SELECT count(*) FROM read_parquet('{out}\\*.parquet')").fetchone()[0]
    print(f"  {folder}: {parts} files, {got:,} rows (source {total:,}), "
          f"{size/1048576:.1f} MB, {time.time()-t0:.0f}s")
    assert got == total
    return out

fact_total = con.execute("SELECT count(*) FROM FactPart").fetchone()[0]
write_parts_expr("FactOut", "FactContractTransactions", PARTS, "_rn", fact_total)
write_parts("DimAwardSlim", "DimAward", AWARD_PARTS, "AwardKey")

# remove the old single-file versions so nothing stale is picked up
for stale in ["FactContractTransactions.parquet", "DimAward.parquet"]:
    p = os.path.join(DATA, stale)
    if os.path.exists(p):
        os.remove(p)
        print(f"  removed stale {stale}")

# ---------------------------------------------------------------- benchmark copies (CSV)
print("\nwriting CSV benchmark copies (scratch only)")
csv_dir = os.path.join(BENCH, "csv_fact")
if os.path.exists(csv_dir):
    shutil.rmtree(csv_dir)
os.makedirs(csv_dir)
per = -(-fact_total // PARTS)
t0 = time.time()
for i in range(PARTS):
    con.execute(f"""
        COPY (SELECT * EXCLUDE (_rn) FROM FactOut WHERE _rn > {i*per} AND _rn <= {(i+1)*per})
        TO '{os.path.join(csv_dir, f"part_{i+1:02d}.csv")}' (FORMAT CSV, HEADER)
    """)
size = sum(os.path.getsize(os.path.join(csv_dir, f)) for f in os.listdir(csv_dir))
print(f"  csv_fact: {PARTS} files, {size/1048576:.1f} MB, {time.time()-t0:.0f}s")

# single-file parquet copy of the fact, for the 1-partition benchmark arm
one = os.path.join(BENCH, "fact_single.parquet")
t0 = time.time()
con.execute(f"COPY (SELECT * EXCLUDE (_rn) FROM FactOut) TO '{one}' (FORMAT PARQUET, COMPRESSION ZSTD)")
print(f"  fact_single.parquet: {os.path.getsize(one)/1048576:.1f} MB, {time.time()-t0:.0f}s")

# ---------------------------------------------------------------- integrity re-check
print("\nintegrity against the validated baseline")
fact_glob = os.path.join(DATA, "FactContractTransactions", "*.parquet").replace("\\", "\\\\")
award_glob = os.path.join(DATA, "DimAward", "*.parquet").replace("\\", "\\\\")
checks = [
    ("fact rows = 6,639,176",
     f"SELECT count(*) FROM read_parquet('{fact_glob}')", 6639176),
    ("distinct awards = 5,832,578",
     f"SELECT count(DISTINCT AwardKey) FROM read_parquet('{fact_glob}')", 5832578),
    ("DimAward rows = 5,832,578",
     f"SELECT count(*) FROM read_parquet('{award_glob}')", 5832578),
]
for label, sql, expect in checks:
    got = con.execute(sql).fetchone()[0]
    print(f"  [{'PASS' if got == expect else 'FAIL'}] {label}  (got {got:,})")
obl = con.execute(f'SELECT sum("Obligation") FROM read_parquet(\'{fact_glob}\')').fetchone()[0]
print(f"  [{'PASS' if abs(float(obl) - 793189920124.27) < 1 else 'FAIL'}] obligations = $793,189,920,124.27  (got ${float(obl):,.2f})")
print("\nREBUILD COMPLETE")
