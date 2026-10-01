import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import duckdb, glob, os, time, json

CSV_DIR = SCRATCH + r"\csv"
STAGE   = SCRATCH + r"\stage2"
TMP     = SCRATCH + r"\tmp"

COLS = [
 # grain / identity
 "contract_transaction_unique_key","contract_award_unique_key","award_id_piid",
 "modification_number","transaction_number","parent_award_id_piid",
 # money
 "federal_action_obligation","total_dollars_obligated","base_and_exercised_options_value",
 "current_total_value_of_award","potential_total_value_of_award",
 "total_outlayed_amount_for_overall_award",
 # dates
 "action_date","action_date_fiscal_year",
 "period_of_performance_start_date","period_of_performance_current_end_date",
 # agency
 "awarding_agency_code","awarding_agency_name","awarding_sub_agency_code","awarding_sub_agency_name",
 "funding_agency_code","funding_agency_name","funding_sub_agency_code","funding_sub_agency_name",
 # recipient
 "recipient_uei","recipient_name","recipient_parent_uei","recipient_parent_name",
 "recipient_country_code","recipient_state_code","recipient_city_name",
 "contracting_officers_determination_of_business_size",
 # place of performance
 "primary_place_of_performance_country_code","primary_place_of_performance_state_code",
 "primary_place_of_performance_county_name","prime_award_transaction_place_of_performance_cd_current",
 # contract attributes
 "award_or_idv_flag","award_type_code","award_type","idv_type",
 "type_of_contract_pricing_code","type_of_contract_pricing",
 "action_type_code","action_type",
 "extent_competed_code","extent_competed","solicitation_procedures",
 "type_of_set_aside_code","type_of_set_aside","number_of_offers_received",
 "naics_code","naics_description","product_or_service_code","product_or_service_code_description",
 "parent_award_type",
 # socio-economic
 "woman_owned_business","veteran_owned_business","service_disabled_veteran_owned_business",
 "minority_owned_business","historically_underutilized_business_zone_hubzone_firm",
 "c8a_program_participant","nonprofit_organization","educational_institution","foreign_owned",
 # description (staging only)
 "transaction_description",
]

con = duckdb.connect(database=":memory:")
con.execute("SET memory_limit='3GB'")
con.execute(f"SET temp_directory='{TMP}'")
con.execute("SET preserve_insertion_order=false")
con.execute("SET threads=4")

sel = ", ".join(f'"{c}"' for c in COLS)
files = sorted(glob.glob(os.path.join(CSV_DIR, "*.csv")))
for i, f in enumerate(files, 1):
    out = os.path.join(STAGE, f"stg_{i}.parquet")
    if os.path.exists(out):
        print("skip", out, flush=True); continue
    t0 = time.time()
    con.execute(f"""
        COPY (
          SELECT {sel}
          FROM read_csv('{f}', header=true, all_varchar=true,
                        quote='"', escape='"', strict_mode=false, ignore_errors=false)
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 300000)
    """)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    print(f"{os.path.basename(f)} -> {os.path.basename(out)} rows={n:,} {time.time()-t0:.0f}s size={os.path.getsize(out)/1048576:.0f}MB", flush=True)
print("STAGE COMPLETE", flush=True)
