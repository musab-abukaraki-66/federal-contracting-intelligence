import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb, json, os
S = SCRATCH + r"\stage\*.parquet"
con = duckdb.connect()
con.execute("SET memory_limit='3GB'"); con.execute(r"SET temp_directory=SCRATCH + r'\tmp'")
con.execute("SET preserve_insertion_order=false"); con.execute("SET threads=4")
con.execute(f"CREATE VIEW t AS SELECT * FROM read_parquet('{S}')")

def q(label, sql):
    print("\n### " + label)
    r = con.execute(sql).df()
    print(r.to_string(index=False, max_colwidth=60))

q("row counts & grain", """
SELECT count(*) n_rows,
       count(DISTINCT contract_transaction_unique_key) dist_txn_key,
       count(DISTINCT contract_award_unique_key) dist_award_key,
       count(DISTINCT award_id_piid) dist_piid,
       count(DISTINCT recipient_uei) dist_uei,
       count(DISTINCT recipient_name) dist_recip_name,
       count(DISTINCT recipient_parent_uei) dist_parent_uei
FROM t""")

q("obligation stats", """
SELECT round(sum(TRY_CAST(federal_action_obligation AS DOUBLE)),0) sum_obl,
       count(*) FILTER (WHERE TRY_CAST(federal_action_obligation AS DOUBLE) < 0) neg_rows,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE)) FILTER (WHERE TRY_CAST(federal_action_obligation AS DOUBLE)<0),0) neg_sum,
       count(*) FILTER (WHERE TRY_CAST(federal_action_obligation AS DOUBLE) = 0) zero_rows,
       count(*) FILTER (WHERE federal_action_obligation IS NULL OR federal_action_obligation='') null_rows,
       round(min(TRY_CAST(federal_action_obligation AS DOUBLE)),0) min_obl,
       round(max(TRY_CAST(federal_action_obligation AS DOUBLE)),0) max_obl
FROM t""")

q("action_date range / fiscal year", """
SELECT min(action_date) min_d, max(action_date) max_d,
       count(*) FILTER (WHERE action_date < '2024-10-01' OR action_date > '2025-09-30') outside_fy,
       count(DISTINCT action_date_fiscal_year) n_fy,
       string_agg(DISTINCT action_date_fiscal_year, ',') fys
FROM t""")

cols = ["awarding_agency_name","awarding_sub_agency_name","funding_agency_name","recipient_uei","recipient_name",
        "recipient_parent_uei","recipient_state_code","recipient_country_code","primary_place_of_performance_state_code",
        "primary_place_of_performance_country_code","naics_code","naics_description","product_or_service_code",
        "extent_competed","type_of_contract_pricing","type_of_set_aside","award_type","action_type","idv_type",
        "award_or_idv_flag","parent_award_type","contracting_officers_determination_of_business_size",
        "number_of_offers_received","transaction_description","prime_award_transaction_place_of_performance_cd_current"]
sel = ",\n".join([f"round(100.0*count(*) FILTER (WHERE \"{c}\" IS NULL OR \"{c}\"='')/count(*),2) AS \"{c}\"" for c in cols])
r = con.execute(f"SELECT {sel} FROM t").df().T
r.columns=["null_pct"]
print("\n### null/blank % by column"); print(r.to_string())

sel2 = ",\n".join([f"count(DISTINCT \"{c}\") AS \"{c}\"" for c in cols])
r2 = con.execute(f"SELECT {sel2} FROM t").df().T
r2.columns=["distinct"]
print("\n### cardinality"); print(r2.to_string())

q("top 10 awarding agencies", """
SELECT awarding_agency_name, count(*) txns,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 10""")

q("top 10 recipients (parent)", """
SELECT recipient_parent_name, count(*) txns,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 10""")

q("UEI -> multiple names", """
SELECT count(*) uei_with_multiple_names FROM (
  SELECT recipient_uei FROM t WHERE recipient_uei IS NOT NULL AND recipient_uei<>''
  GROUP BY 1 HAVING count(DISTINCT recipient_name) > 1)""")

q("award key -> multiple agencies", """
SELECT count(*) awards_multi_agency FROM (
  SELECT contract_award_unique_key FROM t GROUP BY 1
  HAVING count(DISTINCT awarding_sub_agency_name) > 1)""")

q("monthly obligations", """
SELECT substr(action_date,1,7) ym, count(*) txns,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY 1""")

q("award_or_idv_flag mix", """
SELECT award_or_idv_flag, count(*) txns, round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY txns DESC""")

q("action_type mix", """
SELECT coalesce(nullif(action_type,''),'(blank = new award)') action_type, count(*) txns,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY txns DESC LIMIT 12""")

q("extent_competed mix", """
SELECT coalesce(nullif(extent_competed,''),'(blank)') extent_competed, count(*) txns,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC""")

q("place of performance country top", """
SELECT primary_place_of_performance_country_code cc, count(*) txns,
       round(sum(TRY_CAST(federal_action_obligation AS DOUBLE))/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 8""")

q("award-level rollup repetition check", """
SELECT count(*) n_awards,
       count(*) FILTER (WHERE n_distinct_total>1) awards_with_varying_total_dollars_obligated
FROM (SELECT contract_award_unique_key, count(DISTINCT total_dollars_obligated) n_distinct_total
      FROM t GROUP BY 1)""")
