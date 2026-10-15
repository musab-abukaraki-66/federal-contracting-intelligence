"""Pages 02-07 plus the two tooltip pages.

Design system is inherited from Page 01 and is not re-derived here:
  - 212 px navigation rail, 4 macro columns of 279 px with 16 px gutters
  - header block at y=40/58/102, KPI band 158-286, content 306-862
  - Georgia for editorial titles, Segoe UI for everything functional
  - one brass accent, steel/sage/clay/iris as secondary series colours
  - every chart sized so that ~30 px per bar category is available (no scrollbars)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_lib import *           # noqa
from build_report_head import (rail, page_head, footer, MIDDOT, NAV)   # noqa

# ---------------------------------------------------------------- shared page frame
def frame(page_name, kicker, title, standfirst, kpis, kpi_note_row=True):
    """Rail + header + KPI band. Returns the visual list ready for content."""
    v = rail(page_name)
    v += page_head(kicker, title, standfirst, span(3))
    v.append(rect("kpiRuleTop", M_LEFT, 158, CONTENT_W, 1, HAIRLINE, z=1))
    for idx, (nm, label, meas, units, prec, note) in enumerate(kpis):
        x = colx(idx)
        v.append(textbox(nm + "Label", x, 172, COL_W, 14,
                         [{"text": label, "size": 8, "family": UI_SB, "color": MUTED, "spacing": 120}]))
        v.append(card(nm, x - 7, 190, COL_W, 66, meas, units=units, precision=prec, value_size=26))
        if kpi_note_row:
            v.append(textbox(nm + "Note", x, 260, COL_W, 16,
                             [{"text": note, "size": 8, "family": UI, "color": MUTED}]))
        if idx:
            v.append(rect("kpiSep%d" % idx, x - 9, 174, 1, 102, HAIRLINE, z=1))
    v.append(rect("kpiRuleBottom", M_LEFT, 286, CONTENT_W, 1, HAIRLINE, z=1))
    return v


def annotation(name, y, lead, body, width=None):
    return textbox(name, M_LEFT, y, width or span(4), 34, [
        {"text": lead + "  ", "size": 9, "family": UI_SB, "color": BRASS},
        {"text": body, "size": 9, "family": UI, "color": TEXT2}])


def close_page(v, rule_y=868, footer_y=876):
    v.append(rect("footRule", M_LEFT, rule_y, CONTENT_W, 1, HAIRLINE, z=1))
    v.append(footer(y=footer_y))
    return v


# ================================================================ PAGE 02
def page02():
    """Market structure - how dollars are actually transacted, not just how many."""
    kpis = [
        ("kpiBase", "ON NEW AWARDS",        "Base Award Obligations",  1000000000, 1,
         "5.37m base contract actions"),
        ("kpiMod",  "ON EXISTING CONTRACTS","Modification Obligations", 1000000000, 1,
         "funding, options, scope changes"),
        ("kpiDeob", "DE-OBLIGATED",         "De-obligations",           1000000000, 1,
         "terminations and close-outs"),
        ("kpiAvg",  "AVERAGE ACTION",       "Average Transaction Value", 0,         0,
         "mean obligation per action"),
    ]
    v = frame("p02Market",
              "MARKET STRUCTURE " + MIDDOT + " FY2025",
              "Most federal money moves through contracts that already exist",
              "Only 41% of FY2025 obligations went onto new awards. The rest flowed through "
              "modifications, option exercises and funding actions on contracts signed in earlier "
              "years - which is where the real procurement calendar lives.",
              kpis)

    v.append(stacked_column(
        "marketMonthly", M_LEFT, 306, span(4), 250,
        category=cproj("DimDate", "Month Short"),
        values=[mproj("Obligations")],
        series=cproj("DimActionType", "Action Class"),
        title="MONTHLY OBLIGATIONS BY TYPE OF CONTRACT ACTION",
        sort_field=column("DimDate", "Month Short"), sort_dir="Ascending"))

    v.append(annotation(
        "marketNote", 566,
        "Funding actions are the September story.",
        "Base awards stay broadly flat all year. The year-end surge is dominated by funding "
        "actions and option exercises on contracts that were already in place."))

    v.append(rect("rowRule", M_LEFT, 606, CONTENT_W, 1, HAIRLINE, z=1))

    v.append(barchart(
        "pricingFamily", M_LEFT, 622, span(2), 240,
        category=cproj("DimContractType", "Pricing Family"),
        values=[mproj("Obligations")],
        title="PRICING ARRANGEMENT",
        sort_field=measure("Obligations"),
        cat_size=9, margin_factor=36, inner_padding=12))

    v.append(barchart(
        "actionClass", colx(2), 622, span(2), 240,
        category=cproj("DimActionType", "Action Class"),
        values=[mproj("Obligations")],
        title="TYPE OF CONTRACT ACTION",
        sort_field=measure("Obligations"),
        fill=STEEL, cat_size=9, margin_factor=36, inner_padding=12))

    pg, _ = page("p02Market", "Market structure", close_page(v))
    return pg, v


# ================================================================ PAGE 03
def page03():
    """Agency intelligence - who commands the money and how differently they buy."""
    kpis = [
        ("kpiObl",   "OBLIGATIONS",        "Obligations",               1000000000, 1,
         "in the current selection"),
        ("kpiOrgs",  "AWARDING BODIES",    "Awarding Organisations",     1,         0,
         "sub-agencies placing contracts"),
        ("kpiCross", "CROSS-SERVICED",     "Cross-Serviced Obligations", 1000000000, 1,
         "bought by one body, funded by another"),
        ("kpiPer",   "ACTIONS PER AWARD",  "Actions per Award",          0,         2,
         "contract actions per award"),
    ]
    v = frame("p03Agencies",
              "AGENCY INTELLIGENCE " + MIDDOT + " FY2025",
              "Who commands the money",
              "Defense sub-agencies dominate the dollars, but the Defense Logistics Agency shows a "
              "completely different pattern: 3.9 million actions for $55.9bn, against the Navy's "
              "213 thousand actions for $176.6bn.",
              kpis)

    v.append(barchart(
        "subAgencyRank", M_LEFT, 306, span(2), 542,
        category=cproj("DimAgency", "Sub-Agency"),
        values=[mproj("Obligations " + MIDDOT + " Top 10 Sub-Agencies")],
        title="LARGEST AWARDING SUB-AGENCIES",
        sort_field=measure("Obligations " + MIDDOT + " Top 10 Sub-Agencies"),
        cat_size=9, margin_factor=52, inner_padding=14,
        tooltip_page="ttAgency"))

    v.append(barchart(
        "deptRank", colx(2), 306, span(2), 272,
        category=cproj("DimAgency", "Agency Short"),
        values=[mproj("Obligations " + MIDDOT + " Top 8 Departments")],
        title="LARGEST DEPARTMENTS",
        sort_field=measure("Obligations " + MIDDOT + " Top 8 Departments"),
        fill=STEEL, cat_size=9, margin_factor=26, inner_padding=10,
        labels=False, value_axis=True, gridlines=True))

    v.append(table(
        "agencyBehaviour", colx(2), 596, span(2), 252,
        projections=[cproj("DimAgency", "Agency Short"),
                      mproj("Obligations"),
                      mproj("Competed Share"), mproj("Small Business Share")],
        title="HOW EACH DEPARTMENT BUYS",
        sort_field=measure("Obligations"), value_size=9, header_size=8, row_padding=5))

    pg, _ = page("p03Agencies", "Agencies", close_page(v))
    return pg, v


# ================================================================ PAGE 04
def page04():
    """Contractor intelligence - concentration and who sits at the top."""
    kpis = [
        ("kpiRec",  "RECIPIENTS",          "Recipients",           1, 0, "unique entity identifiers"),
        ("kpiTop",  "TOP 10 PARENT SHARE", "Top 10 Parent Share",  0, 1, "of obligations in context"),
        ("kpiHHI",  "CONCENTRATION (HHI)", "Market Concentration (HHI)", 0, 0,
         "below 1,500 is unconcentrated"),
        ("kpiSmall","SMALL BUSINESS SHARE","Small Business Share",  0, 1, "of obligations"),
    ]
    v = frame("p04Contractors",
              "CONTRACTOR INTELLIGENCE " + MIDDOT + " FY2025",
              "Who receives it",
              "104,476 recipients were paid in FY2025, but ten corporate groups took 28.7% of the "
              "money. Small businesses won 71,742 of the entities and 21.3% of the dollars.",
              kpis)

    v.append(barchart(
        "recipientRank", M_LEFT, 306, span(2), 542,
        category=cproj("DimRecipient", "Recipient"),
        values=[mproj("Obligations " + MIDDOT + " Top 10 Recipients")],
        title="LARGEST RECIPIENTS (CONTRACTING ENTITY)",
        sort_field=measure("Obligations " + MIDDOT + " Top 10 Recipients"),
        cat_size=9, margin_factor=54, inner_padding=14,
        tooltip_page="ttRecipient"))

    v.append(barchart(
        "parentRank", colx(2), 306, span(2), 258,
        category=cproj("DimRecipient", "Parent Company"),
        values=[mproj("Obligations " + MIDDOT + " Top 8 Parents")],
        title="LARGEST PARENT COMPANIES (CORPORATE GROUP)",
        sort_field=measure("Obligations " + MIDDOT + " Top 8 Parents"),
        fill=STEEL, cat_size=8, margin_factor=54, inner_padding=10))

    v.append(table(
        "recipientProfile", colx(2), 590, span(2), 258,
        projections=[cproj("DimRecipient", "Business Size"),
                      mproj("Obligations"),
                      mproj("Transactions"), mproj("Average Transaction Value")],
        title="SMALL BUSINESS VERSUS THE REST",
        sort_field=measure("Obligations"), value_size=9, header_size=8, row_padding=6))

    pg, _ = page("p04Contractors", "Contractors", close_page(v))
    return pg, v


# ================================================================ PAGE 05
def page05():
    """Category and competition intelligence - what is bought and how."""
    kpis = [
        ("kpiComp",   "COMPETED",        "Competed Share",     0, 1, "of obligations"),
        ("kpiSet",    "UNDER SET-ASIDE", "Set-Aside Share",    0, 1, "socio-economic programmes"),
        ("kpiSingle", "SINGLE-OFFER",    "Single-Offer Share", 0, 1, "of actions with a recorded count"),
        ("kpiLarge",  "IN ACTIONS >=$100M", "Large Action Share", 0, 1, "from 823 actions"),
    ]
    v = frame("p05Categories",
              "CATEGORY AND COMPETITION " + MIDDOT + " FY2025",
              "What is bought, and how it is bought",
              "Services take $426.6bn against $305.9bn of products and $60.7bn of R&D. Two thirds of "
              "the money is competed - but $214.1bn is placed without competition at all.",
              kpis)

    v.append(barchart(
        "pscRank", M_LEFT, 306, span(2), 542,
        category=cproj("DimPsc", "PSC Description"),
        values=[mproj("Obligations " + MIDDOT + " Top 12 Categories")],
        title="LARGEST PRODUCT AND SERVICE CATEGORIES",
        sort_field=measure("Obligations " + MIDDOT + " Top 12 Categories"),
        cat_size=8, margin_factor=56, inner_padding=12))

    v.append(barchart(
        "sectorRank", colx(2), 306, span(2), 258,
        category=cproj("DimNaics", "NAICS Sector"),
        values=[mproj("Obligations " + MIDDOT + " Top 8 Sectors")],
        title="INDUSTRY SECTOR (NAICS)",
        sort_field=measure("Obligations " + MIDDOT + " Top 8 Sectors"),
        fill=SAGE, cat_size=8, margin_factor=52, inner_padding=10))

    v.append(barchart(
        "competitionRank", colx(2), 590, span(2), 258,
        category=cproj("DimCompetition", "Extent Competed"),
        values=[mproj("Obligations " + MIDDOT + " Top 6 Competition Types")],
        title="HOW THE WORK WAS COMPETED",
        sort_field=measure("Obligations " + MIDDOT + " Top 6 Competition Types"),
        fill=CLAY, cat_size=8, margin_factor=54, inner_padding=10))

    pg, _ = page("p05Categories", "Categories", close_page(v))
    return pg, v


# ================================================================ PAGE 06
def page06():
    """Geographic intelligence - where the contracted work is performed."""
    kpis = [
        ("kpiUS",     "PERFORMED IN THE US", "US Obligations",        1000000000, 1,
         "94% of all obligations"),
        ("kpiForeign","PERFORMED ABROAD",    "Foreign Obligations",   1000000000, 1,
         "led by Japan and Germany"),
        ("kpiStates", "STATES & TERRITORIES","Performance States",    1,          0,
         "with recorded performance"),
        ("kpiCd",     "CONGRESSIONAL DISTRICTS", "Performance Districts", 1,      0,
         "touched by federal contracts"),
    ]
    v = frame("p06Geography",
              "GEOGRAPHIC INTELLIGENCE " + MIDDOT + " FY2025",
              "Where the work happens",
              "Virginia alone absorbs $120.6bn - more than the next two states combined - a direct "
              "consequence of defence and intelligence contracting clustered around Washington.",
              kpis)

    # Map visuals are disabled by a global Power BI security setting on this machine, so the
    # geography story is told with a ranked bar instead of a choropleth. Same data, no dependency
    # on a tenant setting.
    v.append(barchart(
        "stateRank", M_LEFT, 306, span(2), 542,
        category=cproj("DimPlaceOfPerformance", "Performance State"),
        values=[mproj("Obligations " + MIDDOT + " Top 12 States")],
        title="LARGEST STATES BY PLACE OF PERFORMANCE",
        sort_field=measure("Obligations " + MIDDOT + " Top 12 States"),
        cat_size=9, margin_factor=18, inner_padding=14,
        filters=exclude_filter("stateExclude", "DimPlaceOfPerformance",
                                "Performance State", ["(not applicable)"])))

    v.append(barchart(
        "regionSplit", colx(2), 306, span(2), 258,
        category=cproj("DimPlaceOfPerformance", "Performance Region"),
        values=[mproj("Obligations")],
        title="WHERE PERFORMANCE IS RECORDED",
        sort_field=measure("Obligations"),
        fill=SAGE, cat_size=9, margin_factor=40, inner_padding=12))

    v.append(barchart(
        "countryRank", colx(2), 590, span(2), 258,
        category=cproj("DimPlaceOfPerformance", "Performance Country"),
        values=[mproj("Obligations " + MIDDOT + " Top 8 Countries")],
        title="PERFORMANCE OUTSIDE THE UNITED STATES",
        sort_field=measure("Obligations " + MIDDOT + " Top 8 Countries"),
        fill=IRIS, cat_size=9, margin_factor=26, inner_padding=10,
        filters=exclude_filter("countryExclude", "DimPlaceOfPerformance",
                                "Performance Country", ["USA", "(not applicable)"])))

    pg, _ = page("p06Geography", "Geography", close_page(v))
    return pg, v


# ================================================================ PAGE 07
def page07():
    """Award explorer - row-level evidence and the drillthrough target.

    Scoped by default to actions of $100m or more (823 of them). That is a deliberate
    performance decision: DimAward holds 5.83m rows, and grouping a table by Award PIID
    across the whole year times out, while this scope returns in under two seconds.
    Arriving by drillthrough narrows it further to a single recipient or department.
    """
    v = rail("p07Explorer")
    v += page_head(
        "AWARD EXPLORER " + MIDDOT + " FY2025",
        "Down to the individual award",
        "The 823 contract actions of $100m or more - 37.1% of every dollar obligated in FY2025. "
        "Right-click a recipient or a department anywhere in this report to drill through to their "
        "awards. Use the filter pane to widen the scope. Search any PIID on USAspending.gov to open "
        "the full contract record.",
        span(4))

    v.append(rect("ctlRuleTop", M_LEFT, 158, CONTENT_W, 1, HAIRLINE, z=1))
    strip = [("xObl", "OBLIGATIONS", "Obligations", 1000000000, 1),
             ("xTxn", "ACTIONS", "Transactions", 1, 0),
             ("xAwd", "AWARDS", "Awards", 1, 0),
             ("xAvg", "AVERAGE ACTION", "Average Transaction Value", 1000000, 0)]
    for idx, (nm, label, meas, units, prec) in enumerate(strip):
        x = colx(idx)
        v.append(textbox(nm + "Label", x, 172, COL_W, 14,
                         [{"text": label, "size": 8, "family": UI_SB, "color": MUTED, "spacing": 120}]))
        v.append(card(nm, x - 7, 190, COL_W, 58, meas, units=units, precision=prec, value_size=24))
        if idx:
            v.append(rect("stripSep%d" % idx, x - 9, 174, 1, 76, HAIRLINE, z=1))
    v.append(rect("stripRule", M_LEFT, 258, CONTENT_W, 1, HAIRLINE, z=1))

    v.append(action_button("backBtn", M_RIGHT - 118, 168, 118, 26, "BACK",
                            link_type="Back", size=8))

    v.append(table(
        "awardTable", M_LEFT, 276, CONTENT_W, 574,
        # Kept deliberately narrow. DimAward holds 5.83m rows, so every extra dimension column
        # widens the group-by and the query stops returning. This shape measures at ~1.8 seconds.
        projections=[
            cproj("DimAward", "Award PIID"),
            cproj("DimRecipient", "Recipient"),
            cproj("DimAgency", "Agency Short"),
            mproj("Obligations"),
        ],
        title="CONTRACT ACTIONS OF $100M OR MORE",
        sort_field=measure("Obligations"), value_size=9, header_size=8, row_padding=4))

    close_page(v, rule_y=860, footer_y=868)

    pg, _ = page(
        "p07Explorer", "Award explorer", v,
        binding=drillthrough_binding("dtExplorer", [
            ("dtRecipientParam", "dtRecipient", "DimRecipient", "Recipient"),
            ("dtAgencyParam", "dtAgency", "DimAgency", "Agency Short"),
        ]),
        filters={"filters": [
            drillthrough_filter("dtRecipient", "DimRecipient", "Recipient"),
            drillthrough_filter("dtAgency", "DimAgency", "Agency Short"),
            {"name": "explorerScope",
             "field": column("DimActionSize", "Action Size Band"),
             "type": "Categorical",
             "howCreated": "User",
             "filter": {
                 "Version": 2,
                 "From": [{"Name": "b", "Entity": "DimActionSize", "Type": 0}],
                 "Where": [{"Condition": {"In": {
                     "Expressions": [{"Column": {
                         "Expression": {"SourceRef": {"Source": "b"}},
                         "Property": "Action Size Band"}}],
                     "Values": [[{"Literal": {"Value": "'$100M and above'"}}]]}}}],
             }},
        ]})
    return pg, v


# ================================================================ PAGE 08 - method
def page08():
    v = rail("p08Method")
    v += page_head(
        "PROVENANCE " + MIDDOT + " METHOD AND LIMITATIONS",
        "How this report was built",
        "Every figure traces back to a single official archive. Nothing here is modelled, "
        "estimated or imputed.",
        span(3))

    col_w = span(2)
    body = [
        ("mSource", M_LEFT, 170, "SOURCE",
         "USAspending.gov Award Data Archive, \"All Contracts (Full)\" for fiscal year 2025.\n"
         "Archive dated 2026-09-06, retrieved 2026-09-29.\n"
         "1.79 GB compressed, 13.6 GB and 297 columns uncompressed, split across 7 CSV parts.\n"
         "Reference data: USAspending toptier_agencies and data_dictionary API endpoints."),
        ("mGrain", M_LEFT, 330, "GRAIN",
         "One row = one prime-contract transaction (a contract action).\n"
         "6,639,176 rows, all 6,639,176 transaction keys distinct - verified, not assumed.\n"
         "These roll up to 5,832,578 contract awards and 104,476 recipients.\n"
         "Period: 1 October 2024 to 30 September 2025. No row falls outside it."),
        ("mMoney", M_LEFT, 490, "WHAT COUNTS AS MONEY",
         "Only federal_action_obligation is additive and it is the only amount summed here.\n"
         "Award-level columns (total obligated, current value, potential value) are snapshots\n"
         "repeated on every transaction of an award - 132,427 awards carry differing values -\n"
         "so summing them would double-count. They are held at award grain only."),
        ("mQuality", colx(2), 170, "DATA QUALITY DECISIONS",
         "268,758 negative actions (-$53.36bn) kept: de-obligations are real events.\n"
         "694,741 zero-dollar actions kept and counted separately.\n"
         "Blank action type, set-aside, IDV type and performance country are structural,\n"
         "not missing - blank place-of-performance equals the IDV row count exactly.\n"
         "Recipient UEI maps to exactly one name in every case, so UEI is the key."),
        ("mModel", colx(2), 330, "MODEL",
         "Star schema built in DuckDB, exported to Parquet, imported without transformation.\n"
         "One fact table of integer keys plus one decimal measure, eleven dimensions.\n"
         "Fact and DimAward are partitioned so Power BI loads them in parallel.\n"
         "Attribute hierarchies are disabled on keys, which halved the model size."),
        ("mLimits", colx(2), 490, "LIMITATIONS",
         "Single fiscal year - no year-on-year comparison is possible.\n"
         "Prime contracts only: no sub-awards, grants, loans or direct payments.\n"
         "Parent-company mapping follows FPDS registration and occasionally names a foreign\n"
         "subsidiary as the corporate parent (RTX appears under Rockwell Collins Australia).\n"
         "Offers-received is recorded on only 32% of actions and carries a 999 bulk value."),
    ]
    for nm, x, y, head, text in body:
        v.append(textbox(nm + "H", x, y, col_w, 14,
                         [{"text": head, "size": 8, "family": UI_SB, "color": BRASS, "spacing": 120}]))
        v.append(textbox(nm, x, y + 20, col_w, 130,
                         [{"text": text, "size": 9, "family": UI, "color": TEXT2}]))
        v.append(rect(nm + "R", x, y - 10, col_w, 1, HAIRLINE, z=1))

    v.append(textbox("mFigures", M_LEFT, 650, span(4), 60, [
        {"text": "HEADLINE FIGURES, RECONCILED AGAINST SOURCE\n", "size": 8, "family": UI_SB,
         "color": BRASS, "spacing": 120},
        {"text": "$793,189,920,124.27 obligated   " + MIDDOT + "   6,639,176 contract actions   "
                 + MIDDOT + "   5,832,578 awards   " + MIDDOT + "   104,476 recipients   "
                 + MIDDOT + "   Defense 62.0%   " + MIDDOT + "   September 19.0%   "
                 + MIDDOT + "   823 actions of $100m or more carry 37.1% of all dollars",
         "size": 9, "family": UI, "color": TEXT}]))

    close_page(v, rule_y=740, footer_y=748)
    pg, _ = page("p08Method", "Method & sources", v)
    return pg, v


# ================================================================ tooltip pages
TT_W, TT_H = 340, 280


def tooltip_recipient():
    v = [rect("ttBg", 0, 0, TT_W, TT_H, SURFACE, z=0),
         rect("ttAccent", 0, 0, TT_W, 3, BRASS, z=1),
         textbox("ttTitle", 20, 18, TT_W - 40, 34,
                 [{"text": "Recipient profile", "size": 11, "family": SERIF, "color": TEXT}])]
    rows = [("Obligations", "Obligations", 1000000000, 1),
            ("Contract actions", "Transactions", 1, 0),
            ("Awards", "Awards", 1, 0),
            ("Average action", "Average Transaction Value", 0, 0),
            ("Rank by obligations", "Recipient Rank", 1, 0)]
    y = 60
    for i, (label, meas, units, prec) in enumerate(rows):
        v.append(textbox("ttL%d" % i, 20, y + 6, 150, 16,
                         [{"text": label, "size": 8, "family": UI_SB, "color": MUTED}]))
        v.append(card("ttV%d" % i, 150, y - 4, 180, 34, meas, units=units, precision=prec,
                      value_size=13, align="right"))
        v.append(rect("ttR%d" % i, 20, y + 30, TT_W - 40, 1, HAIRLINE, z=1))
        y += 42
    pg, _ = page("ttRecipient", "Tooltip - recipient", v, width=TT_W, height=TT_H,
                 binding={"name": "ttRecipientBinding", "type": "Tooltip"},
                 visibility="HiddenInViewMode", page_type="Tooltip")
    return pg, v


def tooltip_agency():
    v = [rect("ttBg", 0, 0, TT_W, TT_H, SURFACE, z=0),
         rect("ttAccent", 0, 0, TT_W, 3, STEEL, z=1),
         textbox("ttTitle", 20, 18, TT_W - 40, 34,
                 [{"text": "Agency profile", "size": 11, "family": SERIF, "color": TEXT}])]
    rows = [("Obligations", "Obligations", 1000000000, 1),
            ("Contract actions", "Transactions", 1, 0),
            ("Competed share", "Competed Share", 0, 1),
            ("Small business share", "Small Business Share", 0, 1),
            ("Recipients", "Recipients", 1, 0)]
    y = 60
    for i, (label, meas, units, prec) in enumerate(rows):
        v.append(textbox("ttL%d" % i, 20, y + 6, 160, 16,
                         [{"text": label, "size": 8, "family": UI_SB, "color": MUTED}]))
        v.append(card("ttV%d" % i, 160, y - 4, 170, 34, meas, units=units, precision=prec,
                      value_size=13, align="right"))
        v.append(rect("ttR%d" % i, 20, y + 30, TT_W - 40, 1, HAIRLINE, z=1))
        y += 42
    pg, _ = page("ttAgency", "Tooltip - agency", v, width=TT_W, height=TT_H,
                 binding={"name": "ttAgencyBinding", "type": "Tooltip"},
                 visibility="HiddenInViewMode", page_type="Tooltip")
    return pg, v
