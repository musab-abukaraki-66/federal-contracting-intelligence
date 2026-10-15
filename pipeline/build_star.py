"""Project 06 - build the star schema from the staged FY2025 contract transactions.

Input : <SCRATCH>\\stage2\\*.parquet  (63 columns, 6,639,176 rows)
Output: <project>\\02_PowerBI_Ready\\data\\*.parquet  (fact + dimensions, Power BI ready)

Nothing in 01_Raw_Data is read except the two reference files, and nothing there is written.
"""
import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")

import duckdb, os, time, json, io

OUT = PROJECT_ROOT + r"\02_PowerBI_Ready\data"
REF = PROJECT_ROOT + r"\01_Raw_Data\reference"
STAGE = SCRATCH + r"\stage2\*.parquet"
TMP = SCRATCH + r"\tmp"

os.makedirs(OUT, exist_ok=True)
con = duckdb.connect(SCRATCH + r"\star.duckdb")
con.execute("SET memory_limit='3GB'")
con.execute(f"SET temp_directory='{TMP}'")
con.execute("SET preserve_insertion_order=false")
con.execute("SET threads=4")

def step(label, sql):
    t0 = time.time()
    con.execute(sql)
    print(f"  {label:<28} {time.time()-t0:6.1f}s", flush=True)

def n(table):
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

def export(table, name=None):
    name = name or table
    path = os.path.join(OUT, f"{name}.parquet")
    con.execute(f"COPY {table} TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  -> {name}.parquet  rows={n(table):,}  {os.path.getsize(path)/1048576:.1f} MB", flush=True)

print("staging view")
con.execute(f"""
CREATE OR REPLACE VIEW t AS
SELECT
  contract_transaction_unique_key                       AS txn_key,
  contract_award_unique_key                             AS award_key_nat,
  award_id_piid                                         AS piid,
  nullif(parent_award_id_piid,'')                       AS parent_piid,
  nullif(modification_number,'')                        AS mod_number,
  TRY_CAST(federal_action_obligation AS DECIMAL(18,2))  AS obligation,
  TRY_CAST(total_dollars_obligated AS DECIMAL(18,2))    AS award_obligated_snapshot,
  TRY_CAST(current_total_value_of_award AS DECIMAL(18,2))   AS award_current_value,
  TRY_CAST(potential_total_value_of_award AS DECIMAL(18,2)) AS award_potential_value,
  TRY_CAST(action_date AS DATE)                         AS action_date,
  TRY_CAST(nullif(period_of_performance_start_date,'') AS DATE)       AS pop_start,
  TRY_CAST(nullif(substr(period_of_performance_current_end_date,1,10),'') AS DATE) AS pop_end,
  TRY_CAST(nullif(number_of_offers_received,'') AS INTEGER) AS offers,
  -- awarding / funding organisation
  coalesce(nullif(awarding_agency_code,''),'---')       AS aw_agency_code,
  coalesce(nullif(awarding_agency_name,''),'Unknown')   AS aw_agency_name,
  coalesce(nullif(awarding_sub_agency_code,''),'----')  AS aw_sub_code,
  coalesce(nullif(awarding_sub_agency_name,''),'Unknown') AS aw_sub_name,
  coalesce(nullif(funding_agency_code,''),'---')        AS fu_agency_code,
  coalesce(nullif(funding_agency_name,''),'Unknown')    AS fu_agency_name,
  coalesce(nullif(funding_sub_agency_code,''),'----')   AS fu_sub_code,
  coalesce(nullif(funding_sub_agency_name,''),'Unknown') AS fu_sub_name,
  -- recipient
  coalesce(nullif(recipient_uei,''),'(no UEI)')         AS uei,
  coalesce(nullif(recipient_name,''),'Unknown')         AS recipient_name,
  coalesce(nullif(recipient_parent_uei,''),'(no UEI)')  AS parent_uei,
  coalesce(nullif(recipient_parent_name,''),'Unknown')  AS parent_name,
  coalesce(nullif(recipient_country_code,''),'Unknown') AS rec_country,
  coalesce(nullif(recipient_state_code,''),'Unknown')   AS rec_state,
  coalesce(nullif(recipient_city_name,''),'Unknown')    AS rec_city,
  coalesce(nullif(contracting_officers_determination_of_business_size,''),'Not recorded') AS business_size,
  woman_owned_business, veteran_owned_business, service_disabled_veteran_owned_business,
  minority_owned_business, historically_underutilized_business_zone_hubzone_firm,
  c8a_program_participant, nonprofit_organization, educational_institution, foreign_owned,
  -- place of performance
  coalesce(nullif(primary_place_of_performance_country_code,''),'(not applicable)') AS pop_country,
  coalesce(nullif(primary_place_of_performance_state_code,''),'(not applicable)')   AS pop_state,
  coalesce(nullif(primary_place_of_performance_county_name,''),'(not applicable)')  AS pop_county,
  coalesce(nullif(prime_award_transaction_place_of_performance_cd_current,''),'(not applicable)') AS pop_cd,
  -- what was bought
  coalesce(nullif(naics_code,''),'(not recorded)')      AS naics_code,
  coalesce(nullif(naics_description,''),'Not recorded') AS naics_desc,
  coalesce(nullif(product_or_service_code,''),'(not recorded)') AS psc_code,
  coalesce(nullif(product_or_service_code_description,''),'Not recorded') AS psc_desc,
  -- how it was bought
  coalesce(nullif(award_or_idv_flag,''),'Unknown')      AS award_or_idv,
  coalesce(nullif(award_type,''),'(IDV - no award type)') AS award_type,
  coalesce(nullif(idv_type,''),'(not an IDV)')          AS idv_type,
  coalesce(nullif(type_of_contract_pricing,''),'Not recorded') AS pricing,
  coalesce(nullif(parent_award_type,''),'(no parent vehicle)') AS parent_vehicle,
  coalesce(nullif(extent_competed,''),'Not recorded')   AS extent_competed,
  coalesce(nullif(solicitation_procedures,''),'Not recorded') AS solicitation,
  coalesce(nullif(type_of_set_aside,''),'No set-aside recorded') AS set_aside,
  CASE WHEN nullif(action_type,'') IS NULL THEN 'Base award' ELSE action_type END AS action_type
FROM read_parquet('{STAGE}')
""")

# ---------------------------------------------------------------- DimDate
print("dimensions")
step("DimDate", """
CREATE OR REPLACE TABLE DimDate AS
WITH d AS (SELECT unnest(generate_series(DATE '2024-10-01', DATE '2025-09-30', INTERVAL 1 DAY))::DATE AS dt)
SELECT
  CAST(strftime(dt,'%Y%m%d') AS INTEGER)                       AS DateKey,
  dt                                                           AS "Date",
  CASE WHEN month(dt) >= 10 THEN year(dt)+1 ELSE year(dt) END  AS "Fiscal Year",
  'FY' || CAST(CASE WHEN month(dt) >= 10 THEN year(dt)+1 ELSE year(dt) END AS VARCHAR) AS "Fiscal Year Label",
  ((month(dt) + 2) % 12) + 1                                   AS "Fiscal Month Number",
  'Q' || CAST(((((month(dt) + 2) % 12) + 1) - 1) / 3 + 1 AS INTEGER) AS "Fiscal Quarter",
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
FROM d
""")

# ---------------------------------------------------------------- DimAgency
step("DimAgency", f"""
CREATE OR REPLACE TABLE _agency_src AS
SELECT DISTINCT aw_agency_code AS agency_code, aw_agency_name AS agency_name,
                aw_sub_code AS sub_code, aw_sub_name AS sub_name FROM t
UNION
SELECT DISTINCT fu_agency_code, fu_agency_name, fu_sub_code, fu_sub_name FROM t
""")
step("DimAgency + abbreviations", f"""
CREATE OR REPLACE TABLE DimAgency AS
WITH tt AS (
  SELECT unnest(results) AS r
  FROM read_json('{os.path.join(REF,'toptier_agencies.json')}', maximum_object_size=20000000)
), agency_ref AS (
  SELECT r.toptier_code AS code, r.abbreviation AS abbrev, r.agency_slug AS slug FROM tt
)
SELECT
  row_number() OVER (ORDER BY s.agency_name, s.sub_name) AS AgencyKey,
  s.agency_code            AS "Agency Code",
  s.agency_name            AS "Agency",
  coalesce(a.abbrev, '')   AS "Agency Abbreviation",
  CASE WHEN coalesce(a.abbrev,'') = '' THEN s.agency_name ELSE a.abbrev END AS "Agency Short",
  s.sub_code               AS "Sub-Agency Code",
  s.sub_name               AS "Sub-Agency",
  s.agency_name || ' - ' || s.sub_name AS "Agency / Sub-Agency"
FROM _agency_src s
LEFT JOIN agency_ref a ON a.code = s.agency_code
""")

# ---------------------------------------------------------------- DimRecipient
step("DimRecipient", """
CREATE OR REPLACE TABLE DimRecipient AS
SELECT
  row_number() OVER (ORDER BY uei) AS RecipientKey,
  uei                       AS "Recipient UEI",
  recipient_name            AS "Recipient",
  parent_uei                AS "Parent UEI",
  parent_name               AS "Parent Company",
  rec_country               AS "Recipient Country",
  rec_state                 AS "Recipient State",
  rec_city                  AS "Recipient City",
  business_size             AS "Business Size",
  is_wosb                   AS "Woman Owned",
  is_vosb                   AS "Veteran Owned",
  is_sdvosb                 AS "Service-Disabled Veteran Owned",
  is_minority               AS "Minority Owned",
  is_hubzone                AS "HUBZone",
  is_8a                     AS "8(a) Participant",
  is_nonprofit              AS "Nonprofit",
  is_edu                    AS "Educational Institution",
  is_foreign_owned          AS "Foreign Owned"
FROM (
  SELECT uei,
    arg_max(recipient_name, action_date)  AS recipient_name,
    arg_max(parent_uei, action_date)      AS parent_uei,
    arg_max(parent_name, action_date)     AS parent_name,
    arg_max(rec_country, action_date)     AS rec_country,
    arg_max(rec_state, action_date)       AS rec_state,
    arg_max(rec_city, action_date)        AS rec_city,
    arg_max(business_size, action_date)   AS business_size,
    max(woman_owned_business='t')                                     AS is_wosb,
    max(veteran_owned_business='t')                                   AS is_vosb,
    max(service_disabled_veteran_owned_business='t')                  AS is_sdvosb,
    max(minority_owned_business='t')                                  AS is_minority,
    max(historically_underutilized_business_zone_hubzone_firm='t')    AS is_hubzone,
    max(c8a_program_participant='t')                                  AS is_8a,
    max(nonprofit_organization='t')                                   AS is_nonprofit,
    max(educational_institution='t')                                  AS is_edu,
    max(foreign_owned='t')                                            AS is_foreign_owned
  FROM t GROUP BY uei
)
""")

# ---------------------------------------------------------------- DimNaics / DimPsc
step("DimNaics", """
CREATE OR REPLACE TABLE DimNaics AS
WITH d AS (
  SELECT naics_code, naics_desc, count(*) c FROM t GROUP BY 1,2
), best AS (
  SELECT naics_code, arg_max(naics_desc, c) AS naics_desc FROM d GROUP BY 1
)
SELECT row_number() OVER (ORDER BY naics_code) AS NaicsKey,
       naics_code AS "NAICS Code",
       naics_desc AS "NAICS Industry",
       CASE WHEN naics_code = '(not recorded)' THEN '(not recorded)'
            ELSE substr(naics_code,1,2) END AS "NAICS Sector Code",
       naics_code || ' - ' || naics_desc AS "NAICS Code & Industry"
FROM best
""")

step("DimPsc", """
CREATE OR REPLACE TABLE DimPsc AS
WITH d AS (
  SELECT psc_code, psc_desc, count(*) c FROM t GROUP BY 1,2
), best AS (
  SELECT psc_code, arg_max(psc_desc, c) AS psc_desc FROM d GROUP BY 1
)
SELECT row_number() OVER (ORDER BY psc_code) AS PscKey,
       psc_code AS "PSC Code",
       psc_desc AS "PSC Description",
       substr(psc_code,1,1) AS "PSC Group Code",
       CASE
         WHEN psc_code = '(not recorded)' THEN 'Not recorded'
         WHEN substr(psc_code,1,1) BETWEEN '0' AND '9' THEN 'Product'
         WHEN substr(psc_code,1,1) IN ('A') THEN 'Research & Development'
         ELSE 'Service' END AS "PSC Category",
       psc_code || ' - ' || psc_desc AS "PSC Code & Description"
FROM best
""")

# ---------------------------------------------------------------- junk dimensions
step("DimCompetition", """
CREATE OR REPLACE TABLE DimCompetition AS
SELECT row_number() OVER (ORDER BY extent_competed, solicitation, set_aside) AS CompetitionKey,
       extent_competed AS "Extent Competed",
       solicitation    AS "Solicitation Procedure",
       set_aside       AS "Set-Aside Type",
       CASE WHEN extent_competed IN ('FULL AND OPEN COMPETITION',
                                     'FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES',
                                     'COMPETED UNDER SAP',
                                     'COMPETITIVE DELIVERY ORDER',
                                     'FOLLOW ON TO COMPETED ACTION')
            THEN 'Competed' ELSE 'Not competed' END AS "Competition Status",
       CASE WHEN set_aside = 'No set-aside recorded' THEN 'No set-aside'
            WHEN set_aside = 'NO SET ASIDE USED.'    THEN 'No set-aside'
            ELSE 'Set-aside' END AS "Set-Aside Flag"
FROM (SELECT DISTINCT extent_competed, solicitation, set_aside FROM t)
""")

step("DimContractType", """
CREATE OR REPLACE TABLE DimContractType AS
SELECT row_number() OVER (ORDER BY award_or_idv, award_type, idv_type, pricing) AS ContractTypeKey,
       award_or_idv   AS "Award or IDV",
       award_type     AS "Award Type",
       idv_type       AS "IDV Type",
       pricing        AS "Pricing Type",
       parent_vehicle AS "Parent Vehicle Type",
       CASE WHEN pricing LIKE 'FIRM FIXED PRICE%' OR pricing LIKE 'FIXED PRICE%' THEN 'Fixed price'
            WHEN pricing LIKE 'COST%'                                           THEN 'Cost reimbursement'
            WHEN pricing IN ('TIME AND MATERIALS','LABOR HOURS')                THEN 'Time & materials'
            ELSE 'Other / not recorded' END AS "Pricing Family"
FROM (SELECT DISTINCT award_or_idv, award_type, idv_type, pricing, parent_vehicle FROM t)
""")

step("DimActionType", """
CREATE OR REPLACE TABLE DimActionType AS
SELECT row_number() OVER (ORDER BY action_type) AS ActionTypeKey,
       action_type AS "Action Type",
       CASE WHEN action_type = 'Base award' THEN 'Base award'
            WHEN action_type IN ('TERMINATE FOR CONVENIENCE (COMPLETE OR PARTIAL)',
                                 'TERMINATE FOR DEFAULT (COMPLETE OR PARTIAL)',
                                 'TERMINATE FOR CAUSE','LEGAL CONTRACT CANCELLATION',
                                 'CLOSE OUT','VENDOR TERMINATION') THEN 'Termination / close-out'
            WHEN action_type IN ('EXERCISE AN OPTION') THEN 'Option exercise'
            WHEN action_type IN ('FUNDING ONLY ACTION') THEN 'Funding action'
            WHEN action_type IN ('ENTITY ADDRESS CHANGE','OTHER ADMINISTRATIVE ACTION',
                                 'TRANSFER ACTION','NOVATION AGREEMENT') THEN 'Administrative'
            ELSE 'Scope modification' END AS "Action Class"
FROM (SELECT DISTINCT action_type FROM t)
""")

step("DimPlaceOfPerformance", """
CREATE OR REPLACE TABLE DimPlaceOfPerformance AS
SELECT row_number() OVER (ORDER BY pop_country, pop_state, pop_county, pop_cd) AS PlaceKey,
       pop_country AS "Performance Country",
       pop_state   AS "Performance State",
       pop_county  AS "Performance County",
       pop_cd      AS "Performance Congressional District",
       CASE WHEN pop_country = 'USA' THEN 'United States'
            WHEN pop_country = '(not applicable)' THEN 'Not applicable (IDV)'
            ELSE 'Outside the United States' END AS "Performance Region"
FROM (SELECT DISTINCT pop_country, pop_state, pop_county, pop_cd FROM t)
""")

# ---------------------------------------------------------------- DimAward
step("DimAward", """
CREATE OR REPLACE TABLE DimAward AS
SELECT row_number() OVER (ORDER BY award_key_nat) AS AwardKey,
       award_key_nat AS "Award Unique Key",
       piid          AS "Award PIID",
       parent_piid   AS "Parent Award PIID",
       award_or_idv  AS "Award or IDV",
       award_current_value   AS "Award Current Value",
       award_potential_value AS "Award Potential Value",
       pop_start AS "Performance Start",
       pop_end   AS "Performance End",
       'https://www.usaspending.gov/award/' || award_key_nat || '/' AS "USAspending Link"
FROM (
  SELECT award_key_nat,
         arg_max(piid, action_date)                  AS piid,
         arg_max(parent_piid, action_date)           AS parent_piid,
         arg_max(award_or_idv, action_date)          AS award_or_idv,
         arg_max(award_current_value, action_date)   AS award_current_value,
         arg_max(award_potential_value, action_date) AS award_potential_value,
         arg_max(pop_start, action_date)             AS pop_start,
         arg_max(pop_end, action_date)               AS pop_end
  FROM t GROUP BY award_key_nat
)
""")

for tb in ["DimDate","DimAgency","DimRecipient","DimNaics","DimPsc","DimCompetition",
           "DimContractType","DimActionType","DimPlaceOfPerformance","DimAward"]:
    print(f"    {tb:<24} {n(tb):>10,} rows", flush=True)

# ---------------------------------------------------------------- Fact
print("fact")
step("FactContractTransactions", """
CREATE OR REPLACE TABLE FactContractTransactions AS
SELECT
  CAST(strftime(t.action_date,'%Y%m%d') AS INTEGER)   AS DateKey,
  aw.AgencyKey                                        AS AgencyKey,
  fu.AgencyKey                                        AS FundingAgencyKey,
  r.RecipientKey                                      AS RecipientKey,
  aw2.AwardKey                                        AS AwardKey,
  nc.NaicsKey                                         AS NaicsKey,
  ps.PscKey                                           AS PscKey,
  cp.CompetitionKey                                   AS CompetitionKey,
  ct.ContractTypeKey                                  AS ContractTypeKey,
  act.ActionTypeKey                                    AS ActionTypeKey,
  pl.PlaceKey                                         AS PlaceKey,
  t.obligation                                        AS "Obligation",
  t.offers                                            AS "Offers Received"
FROM t
JOIN DimAgency aw   ON aw.\"Agency Code\"=t.aw_agency_code AND aw.\"Sub-Agency Code\"=t.aw_sub_code AND aw.\"Sub-Agency\"=t.aw_sub_name AND aw.\"Agency\"=t.aw_agency_name
JOIN DimAgency fu   ON fu.\"Agency Code\"=t.fu_agency_code AND fu.\"Sub-Agency Code\"=t.fu_sub_code AND fu.\"Sub-Agency\"=t.fu_sub_name AND fu.\"Agency\"=t.fu_agency_name
JOIN DimRecipient r ON r.\"Recipient UEI\"=t.uei
JOIN DimAward aw2   ON aw2.\"Award Unique Key\"=t.award_key_nat
JOIN DimNaics nc    ON nc.\"NAICS Code\"=t.naics_code
JOIN DimPsc ps      ON ps.\"PSC Code\"=t.psc_code
JOIN DimCompetition cp ON cp.\"Extent Competed\"=t.extent_competed AND cp.\"Solicitation Procedure\"=t.solicitation AND cp.\"Set-Aside Type\"=t.set_aside
JOIN DimContractType ct ON ct.\"Award or IDV\"=t.award_or_idv AND ct.\"Award Type\"=t.award_type AND ct.\"IDV Type\"=t.idv_type AND ct.\"Pricing Type\"=t.pricing AND ct.\"Parent Vehicle Type\"=t.parent_vehicle
JOIN DimActionType act ON act.\"Action Type\"=t.action_type
JOIN DimPlaceOfPerformance pl ON pl.\"Performance Country\"=t.pop_country AND pl.\"Performance State\"=t.pop_state AND pl.\"Performance County\"=t.pop_county AND pl.\"Performance Congressional District\"=t.pop_cd
""")

print(f"    FactContractTransactions {n('FactContractTransactions'):>10,} rows", flush=True)

# ---------------------------------------------------------------- integrity checks
print("integrity")
checks = {
 "fact rows == staged rows":
   "SELECT (SELECT count(*) FROM FactContractTransactions) = (SELECT count(*) FROM t)",
 "obligation total preserved":
   "SELECT abs((SELECT sum(\"Obligation\") FROM FactContractTransactions) - (SELECT sum(obligation) FROM t)) < 0.5",
 "no null keys":
   """SELECT count(*)=0 FROM FactContractTransactions
      WHERE DateKey IS NULL OR AgencyKey IS NULL OR FundingAgencyKey IS NULL OR RecipientKey IS NULL
         OR AwardKey IS NULL OR NaicsKey IS NULL OR PscKey IS NULL OR CompetitionKey IS NULL
         OR ContractTypeKey IS NULL OR ActionTypeKey IS NULL OR PlaceKey IS NULL""",
 "every DateKey exists in DimDate":
   "SELECT count(*)=0 FROM FactContractTransactions f LEFT JOIN DimDate d USING (DateKey) WHERE d.DateKey IS NULL",
}
ok = True
for label, sql in checks.items():
    res = con.execute(sql).fetchone()[0]
    ok = ok and bool(res)
    print(f"  [{'PASS' if res else 'FAIL'}] {label}", flush=True)

print("export")
for tb in ["DimDate","DimAgency","DimRecipient","DimNaics","DimPsc","DimCompetition",
           "DimContractType","DimActionType","DimPlaceOfPerformance","DimAward",
           "FactContractTransactions"]:
    export(tb)

total = sum(os.path.getsize(os.path.join(OUT,f)) for f in os.listdir(OUT) if f.endswith('.parquet'))
print(f"TOTAL EXPORT {total/1048576:.1f} MB")
print("STAR BUILD COMPLETE" if ok else "STAR BUILD COMPLETE WITH FAILED CHECKS")
