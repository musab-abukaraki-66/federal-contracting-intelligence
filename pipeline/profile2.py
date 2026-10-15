import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb
con = duckdb.connect(); con.execute("SET memory_limit='3GB'"); con.execute(r"SET temp_directory=SCRATCH + r'\tmp'")
con.execute("SET preserve_insertion_order=false"); con.execute("SET threads=4")
con.execute(r"CREATE VIEW t AS SELECT *, TRY_CAST(federal_action_obligation AS DOUBLE) AS obl FROM read_parquet(SCRATCH + r'\stage\*.parquet')")
def q(l,s):
    print("\n### "+l); print(con.execute(s).df().to_string(index=False,max_colwidth=70))

q("Rockwell Collins Australia anomaly", """
SELECT recipient_name, recipient_country_code, awarding_agency_name, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t WHERE recipient_parent_name='ROCKWELL COLLINS AUSTRALIA PTY LIMITED'
GROUP BY 1,2,3 ORDER BY obl_bn DESC LIMIT 8""")

q("recipient concentration", """
WITH r AS (SELECT recipient_parent_uei, sum(obl) o FROM t GROUP BY 1),
     s AS (SELECT o, row_number() OVER (ORDER BY o DESC) rn, sum(o) OVER () tot FROM r)
SELECT round(100*sum(o) FILTER (WHERE rn<=10)/max(tot),1) top10_pct,
       round(100*sum(o) FILTER (WHERE rn<=50)/max(tot),1) top50_pct,
       round(100*sum(o) FILTER (WHERE rn<=100)/max(tot),1) top100_pct,
       round(100*sum(o) FILTER (WHERE rn<=1000)/max(tot),1) top1000_pct
FROM s""")

q("award size distribution (by transaction obligation)", """
SELECT CASE WHEN obl<0 THEN 'a. negative (de-obligation)'
            WHEN obl=0 THEN 'b. zero'
            WHEN obl<10000 THEN 'c. <10K'
            WHEN obl<250000 THEN 'd. 10K-250K'
            WHEN obl<1000000 THEN 'e. 250K-1M'
            WHEN obl<10000000 THEN 'f. 1M-10M'
            WHEN obl<100000000 THEN 'g. 10M-100M'
            ELSE 'h. >=100M' END bucket,
       count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY 1""")

q("small business share", """
SELECT contracting_officers_determination_of_business_size sz, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC""")

q("top 12 PSC", """
SELECT product_or_service_code psc, any_value(product_or_service_code_description) descr,
       count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 12""")

q("top 12 NAICS", """
SELECT naics_code, any_value(naics_description) descr, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 12""")

q("top 12 states (place of performance)", """
SELECT primary_place_of_performance_state_code st, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t WHERE primary_place_of_performance_country_code='USA' GROUP BY 1 ORDER BY obl_bn DESC LIMIT 12""")

q("set-aside mix (non blank)", """
SELECT type_of_set_aside, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t WHERE type_of_set_aside<>'' GROUP BY 1 ORDER BY obl_bn DESC LIMIT 10""")

q("pricing type mix", """
SELECT type_of_contract_pricing, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 10""")

q("PSC first char (category) coverage", """
SELECT substr(product_or_service_code,1,1) c, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY obl_bn DESC LIMIT 12""")

q("distinct offices / parent piid", """
SELECT count(DISTINCT awarding_sub_agency_code) subagency_codes,
       count(DISTINCT parent_award_id_piid) parent_piids,
       count(DISTINCT naics_code) naics,
       count(DISTINCT product_or_service_code) psc,
       count(DISTINCT recipient_city_name) cities,
       count(DISTINCT primary_place_of_performance_county_name) counties
FROM t""")

q("DoD sub-agency split", """
SELECT awarding_sub_agency_name, count(*) txns, round(sum(obl)/1e9,2) obl_bn
FROM t WHERE awarding_agency_name='Department of Defense' GROUP BY 1 ORDER BY obl_bn DESC LIMIT 8""")

q("competition by fiscal quarter", """
SELECT CASE WHEN substr(action_date,1,7) IN ('2024-10','2024-11','2024-12') THEN 'Q1'
            WHEN substr(action_date,1,7) IN ('2025-01','2025-02','2025-03') THEN 'Q2'
            WHEN substr(action_date,1,7) IN ('2025-04','2025-05','2025-06') THEN 'Q3' ELSE 'Q4' END fq,
       round(100.0*sum(obl) FILTER (WHERE extent_competed IN ('FULL AND OPEN COMPETITION','FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES','COMPETED UNDER SAP'))/sum(obl),1) competed_pct,
       round(sum(obl)/1e9,2) obl_bn
FROM t GROUP BY 1 ORDER BY 1""")
