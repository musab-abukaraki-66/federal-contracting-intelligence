import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb, os
D = PROJECT_ROOT + r"\02_PowerBI_Ready\data"
con = duckdb.connect(); con.execute("SET memory_limit='3GB'"); con.execute(r"SET temp_directory=SCRATCH + r'\tmp'")
con.execute(f"CREATE VIEW F AS SELECT * FROM read_parquet('{os.path.join(D,'FactContractTransactions','*.parquet')}')")
for t in ["DimDate","DimAgency","DimRecipient","DimNaics","DimPsc","DimCompetition","DimContractType","DimActionType","DimPlaceOfPerformance","DimActionSize"]:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{os.path.join(D,t+'.parquet')}')")
def q(l,s):
    print("\n### "+l); print(con.execute(s).df().to_string(index=False,max_colwidth=46))

q("P02 action class mix", """
SELECT a."Action Class" cls, count(*) txns, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimActionType a USING(ActionTypeKey) GROUP BY 1 ORDER BY bn DESC""")
q("P02 pricing family", """
SELECT c."Pricing Family" fam, count(*) txns, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimContractType c USING(ContractTypeKey) GROUP BY 1 ORDER BY bn DESC""")
q("P02 award vs idv", """
SELECT c."Award or IDV" k, count(*) txns, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimContractType c USING(ContractTypeKey) GROUP BY 1 ORDER BY bn DESC""")
q("P03 top sub-agencies", """
SELECT a."Sub-Agency" s, a."Agency Short" ag, count(*) txns, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimAgency a USING(AgencyKey) GROUP BY 1,2 ORDER BY bn DESC LIMIT 10""")
q("P03 cross-serviced", """
SELECT round(sum(f."Obligation")/1e9,1) cross_bn,
       round(100.0*sum(f."Obligation")/(SELECT sum("Obligation") FROM F),1) pct
FROM F f WHERE f.AgencyKey <> f.FundingAgencyKey""")
q("P04 recipients vs parents", """
SELECT count(DISTINCT r."Recipient") recipients, count(DISTINCT r."Parent Company") parents
FROM F f JOIN DimRecipient r USING(RecipientKey)""")
q("P04 business size", """
SELECT r."Business Size" sz, count(DISTINCT r."Recipient") n, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimRecipient r USING(RecipientKey) GROUP BY 1 ORDER BY bn DESC""")
q("P04 socio-economic", """
SELECT 'Woman owned' k, round(sum(f."Obligation")/1e9,1) bn FROM F f JOIN DimRecipient r USING(RecipientKey) WHERE r."Woman Owned"
UNION ALL SELECT 'Veteran owned', round(sum(f."Obligation")/1e9,1) FROM F f JOIN DimRecipient r USING(RecipientKey) WHERE r."Veteran Owned"
UNION ALL SELECT 'Service-disabled veteran', round(sum(f."Obligation")/1e9,1) FROM F f JOIN DimRecipient r USING(RecipientKey) WHERE r."Service-Disabled Veteran Owned"
UNION ALL SELECT 'Minority owned', round(sum(f."Obligation")/1e9,1) FROM F f JOIN DimRecipient r USING(RecipientKey) WHERE r."Minority Owned"
UNION ALL SELECT 'HUBZone', round(sum(f."Obligation")/1e9,1) FROM F f JOIN DimRecipient r USING(RecipientKey) WHERE r."HUBZone"
UNION ALL SELECT '8(a) participant', round(sum(f."Obligation")/1e9,1) FROM F f JOIN DimRecipient r USING(RecipientKey) WHERE r."8(a) Participant"
ORDER BY bn DESC""")
q("P05 psc category", """
SELECT p."PSC Category" c, count(*) txns, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimPsc p USING(PscKey) GROUP BY 1 ORDER BY bn DESC""")
q("P05 naics sector top", """
SELECT n."NAICS Sector Code" sec, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimNaics n USING(NaicsKey) GROUP BY 1 ORDER BY bn DESC LIMIT 8""")
q("P05 set-aside", """
SELECT c."Set-Aside Type" sa, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimCompetition c USING(CompetitionKey) WHERE c."Set-Aside Flag"='Set-aside'
GROUP BY 1 ORDER BY bn DESC LIMIT 8""")
q("P06 region split", """
SELECT p."Performance Region" r, count(*) txns, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimPlaceOfPerformance p USING(PlaceKey) GROUP BY 1 ORDER BY bn DESC""")
q("P06 top states", """
SELECT p."Performance State" st, round(sum(f."Obligation")/1e9,1) bn
FROM F f JOIN DimPlaceOfPerformance p USING(PlaceKey)
WHERE p."Performance Country"='USA' GROUP BY 1 ORDER BY bn DESC LIMIT 12""")
q("P06 foreign top", """
SELECT p."Performance Country" c, round(sum(f."Obligation")/1e9,2) bn
FROM F f JOIN DimPlaceOfPerformance p USING(PlaceKey)
WHERE p."Performance Country" NOT IN ('USA','(not applicable)') GROUP BY 1 ORDER BY bn DESC LIMIT 8""")
q("P06 congressional districts", """
SELECT count(DISTINCT p."Performance Congressional District") cds FROM F f JOIN DimPlaceOfPerformance p USING(PlaceKey)""")
