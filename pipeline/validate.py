import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb, json, os
D = PROJECT_ROOT + r"\02_PowerBI_Ready\data"
con = duckdb.connect(); con.execute("SET memory_limit='3GB'"); con.execute(r"SET temp_directory=SCRATCH + r'\tmp'")
for t in ["FactContractTransactions","DimDate","DimAgency","DimRecipient","DimCompetition","DimPsc","DimNaics","DimPlaceOfPerformance","DimContractType","DimActionType","DimAward"]:
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{os.path.join(D,t+'.parquet')}')")
q = lambda s: con.execute(s).fetchone()
out = {}
out["Obligations"]            = q('SELECT sum("Obligation") FROM FactContractTransactions')[0]
out["Transactions"]           = q('SELECT count(*) FROM FactContractTransactions')[0]
out["Awards"]                 = q('SELECT count(DISTINCT "AwardKey") FROM FactContractTransactions')[0]
out["Recipients"]             = q('SELECT count(DISTINCT "RecipientKey") FROM FactContractTransactions')[0]
out["Awarding Organisations"] = q('SELECT count(DISTINCT "AgencyKey") FROM FactContractTransactions')[0]
out["New Obligations"]        = q('SELECT sum("Obligation") FROM FactContractTransactions WHERE "Obligation">0')[0]
out["De-obligations"]         = q('SELECT sum("Obligation") FROM FactContractTransactions WHERE "Obligation"<0')[0]
out["Zero-Dollar Actions"]    = q('SELECT count(*) FROM FactContractTransactions WHERE "Obligation"=0')[0]
out["Large Actions >=100M"]   = q('SELECT count(*) FROM FactContractTransactions WHERE "Obligation">=100000000')[0]
out["Large Action Obligations"]=q('SELECT sum("Obligation") FROM FactContractTransactions WHERE "Obligation">=100000000')[0]
out["Competed Obligations"]   = q('SELECT sum(f."Obligation") FROM FactContractTransactions f JOIN DimCompetition c USING("CompetitionKey") WHERE c."Competition Status"=\'Competed\'')[0]
out["Small Business Obligations"] = q('SELECT sum(f."Obligation") FROM FactContractTransactions f JOIN DimRecipient r USING("RecipientKey") WHERE r."Business Size"=\'SMALL BUSINESS\'')[0]
out["Set-Aside Obligations"]  = q('SELECT sum(f."Obligation") FROM FactContractTransactions f JOIN DimCompetition c USING("CompetitionKey") WHERE c."Set-Aside Flag"=\'Set-aside\'')[0]
out["Obligations in September"]= q('SELECT sum(f."Obligation") FROM FactContractTransactions f JOIN DimDate d USING("DateKey") WHERE d."Fiscal Month Number"=12')[0]
out["Obligations in Final Quarter"]=q('SELECT sum(f."Obligation") FROM FactContractTransactions f JOIN DimDate d USING("DateKey") WHERE d."Fiscal Quarter"=\'Q4\'')[0]
out["Average Offers Received"]= q('SELECT avg("Offers Received") FROM FactContractTransactions WHERE "Offers Received" IS NOT NULL')[0]
out["Cross-Serviced Obligations"]=q('SELECT sum("Obligation") FROM FactContractTransactions WHERE "AgencyKey"<>"FundingAgencyKey"')[0]
out["DoD Obligations"]        = q('SELECT sum(f."Obligation") FROM FactContractTransactions f JOIN DimAgency a USING("AgencyKey") WHERE a."Agency"=\'Department of Defense\'')[0]
tot = out["Obligations"]
print(json.dumps({k:(float(v) if v is not None else None) for k,v in out.items()}, indent=1))
print()
print("Derived:")
print(f'  Competed share      {out["Competed Obligations"]/tot:.4%}')
print(f'  Small business share {out["Small Business Obligations"]/tot:.4%}')
print(f'  Set-aside share     {out["Set-Aside Obligations"]/tot:.4%}')
print(f'  September share     {out["Obligations in September"]/tot:.4%}')
print(f'  Final quarter share {out["Obligations in Final Quarter"]/tot:.4%}')
print(f'  Large action share  {out["Large Action Obligations"]/tot:.4%}')
print(f'  DoD share           {out["DoD Obligations"]/tot:.4%}')
print(f'  Actions per award   {out["Transactions"]/out["Awards"]:.4f}')
print(f'  Avg transaction     {tot/out["Transactions"]:,.2f}')
print()
print("Top 10 parent share:")
print(con.execute('''
WITH r AS (SELECT rr."Parent Company" p, sum(f."Obligation") o
           FROM FactContractTransactions f JOIN DimRecipient rr USING("RecipientKey") GROUP BY 1),
     s AS (SELECT o, row_number() OVER (ORDER BY o DESC) rn, sum(o) OVER () tot FROM r)
SELECT round(100*sum(o) FILTER (WHERE rn<=10)/max(tot),2) AS top10_pct FROM s''').df().to_string(index=False))
print()
print("HHI (parent company):")
print(con.execute('''
WITH r AS (SELECT rr."Parent Company" p, sum(f."Obligation") o
           FROM FactContractTransactions f JOIN DimRecipient rr USING("RecipientKey") GROUP BY 1),
     t AS (SELECT o/(SELECT sum(o) FROM r) sh FROM r)
SELECT round(sum(sh*sh)*10000,1) AS hhi FROM t''').df().to_string(index=False))
