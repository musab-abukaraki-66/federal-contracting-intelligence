"""Generate the PBIR report definition for Project 06 - Federal Contracting Intelligence."""
import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")

import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_lib import *   # noqa

PBIP_ROOT  = PROJECT_ROOT + r"\02_PowerBI_Ready\pbip"
REPORT_DIR = os.path.join(PBIP_ROOT, "FederalContracting.Report")
MODEL_DIR  = os.path.join(PBIP_ROOT, "FederalContracting.SemanticModel")
THEME_SRC  = PROJECT_ROOT + r"\02_PowerBI_Ready\design\FederalLedger.json"
# Base theme is copied out of a Power BI Desktop-generated reference project.
# See docs/03-completion-report.md for why that reference project exists.
BASE_THEME = os.path.join(SCRATCH, "ref", "Ref.Report", "StaticResources",
                          "SharedResources", "BaseThemes", "Fluent2-CY26SU09.json")

MIDDOT = "\u00b7"
SOURCE_NOTE = ("Source: USAspending.gov Award Data Archive, All Contracts (Full) FY2025, "
               "archive dated 2026-09-06, retrieved 2026-09-29. "
               "One row = one prime-contract action. Obligations are net of de-obligations.")

NAV = [
    ("p01Executive",   "Executive brief"),
    ("p02Market",      "Market structure"),
    ("p03Agencies",    "Agencies"),
    ("p04Contractors", "Contractors"),
    ("p05Categories",  "Categories"),
    ("p06Geography",   "Geography"),
    ("p07Explorer",    "Award explorer"),
    ("p08Method",      "Method & sources"),
]


# ---------------------------------------------------------------- shared furniture
def rail(active):
    """Left navigation rail - identical on every page."""
    v = [
        rect("railBackground", 0, 0, RAIL_W, PAGE_H, SURFACE, z=0),
        rect("railEdge", RAIL_W - 1, 0, 1, PAGE_H, HAIRLINE, z=1),
        rect("railBrassMark", 28, 46, 26, 3, BRASS, z=2),
        textbox("railKicker", 28, 60, 168, 16,
                [{"text": "PROJECT 06", "size": 8, "family": UI_SB, "color": MUTED, "spacing": 120}], z=2),
        textbox("railTitle", 28, 80, 168, 84,
                [{"text": "Federal Contracting Intelligence", "size": 15, "family": SERIF, "color": TEXT}], z=2),
        rect("railRule", 28, 176, 156, 1, HAIRLINE, z=2),
    ]
    y = 200
    for idx, (pname, label) in enumerate(NAV):
        is_active = pname == active
        v.append(nav_button("nav%d" % idx, 0, y, RAIL_W - 1, 36, label, pname, active=is_active))
        if is_active:
            v.append(rect("navMark%d" % idx, 0, y, 3, 36, BRASS, z=3))
        y += 38
    v.append(rect("railRule2", 28, y + 14, 156, 1, HAIRLINE, z=2))
    v.append(textbox("railFooter", 28, PAGE_H - 104, 168, 84, [
        {"text": "USAspending.gov\n", "size": 8, "family": UI_SB, "color": MUTED},
        {"text": "Award Data Archive\nPrime contracts, FY2025\n1 Oct 2024 - 30 Sep 2025",
         "size": 8, "family": UI, "color": MUTED},
    ], z=2))
    return v


def page_head(kicker, title, standfirst=None, standfirst_width=None):
    v = [
        textbox("headKicker", M_LEFT, 40, 700, 16,
                [{"text": kicker, "size": 8, "family": UI_SB, "color": BRASS, "spacing": 140}]),
        textbox("headTitle", M_LEFT, 58, 900, 40,
                [{"text": title, "size": 24, "family": SERIF, "color": TEXT}]),
    ]
    if standfirst:
        v.append(textbox("headStandfirst", M_LEFT, 102, standfirst_width or span(3), 40,
                         [{"text": standfirst, "size": 10, "family": UI, "color": TEXT2}]))
    return v


def footer(name="pageFooter", text=SOURCE_NOTE, y=PAGE_H - 36):
    return textbox(name, M_LEFT, y, CONTENT_W, 22,
                   [{"text": text, "size": 8, "family": UI, "color": MUTED}])


# ---------------------------------------------------------------- page 01
KPIS = [
    ("kpiObligations", "TOTAL OBLIGATIONS",   "Obligations",         1000000000, 1,
     "net of $53.4bn de-obligated"),
    ("kpiActions",     "CONTRACT ACTIONS",    "Transactions",        1000000,    2,
     "across 5.83m contract awards"),
    ("kpiRecipients",  "RECIPIENTS",          "Recipients",          1,          0,
     "unique entity identifiers"),
    ("kpiTop10",       "TOP 10 PARENT SHARE", "Top 10 Parent Share", 0,          1,
     "held by ten corporate groups"),
]


def page01():
    v = rail("p01Executive")
    v += page_head(
        "FISCAL YEAR 2025 " + MIDDOT + " PRIME CONTRACT OBLIGATIONS",
        "The shape of a federal contracting year",
        "Every prime-contract action the U.S. government reported to FPDS between 1 October 2024 "
        "and 30 September 2025. Deliberately unfiltered: this is the baseline the rest of the "
        "report is measured against.",
        span(3))

    # -- KPI band -----------------------------------------------------------
    v.append(rect("kpiRuleTop", M_LEFT, 158, CONTENT_W, 1, HAIRLINE, z=1))
    for idx, (nm, label, meas, units, prec, note) in enumerate(KPIS):
        x = colx(idx)
        v.append(textbox(nm + "Label", x, 172, COL_W, 14,
                         [{"text": label, "size": 8, "family": UI_SB, "color": MUTED, "spacing": 120}]))
        v.append(card(nm, x - 7, 190, COL_W, 66, meas, units=units, precision=prec, value_size=26))
        v.append(textbox(nm + "Note", x, 260, COL_W, 16,
                         [{"text": note, "size": 8, "family": UI, "color": MUTED}]))
        if idx:
            v.append(rect("kpiSep%d" % idx, x - 9, 174, 1, 102, HAIRLINE, z=1))
    v.append(rect("kpiRuleBottom", M_LEFT, 286, CONTENT_W, 1, HAIRLINE, z=1))

    # -- primary story ------------------------------------------------------
    v.append(columnchart(
        "trendMonthly", M_LEFT, 306, span(3), 228,
        category=cproj("DimDate", "Month Short"),
        values=[mproj("Obligations")],
        title="OBLIGATIONS BY MONTH",
        sort_field=column("DimDate", "Month Short"), sort_dir="Ascending"))

    v.append(barchart(
        "topDepartments", colx(3), 300, COL_W, 284,
        category=cproj("DimAgency", "Agency Short"),
        values=[mproj("Obligations " + MIDDOT + " Top 8 Departments")],
        title="LARGEST DEPARTMENTS",
        sort_field=measure("Obligations " + MIDDOT + " Top 8 Departments"),
        cat_size=8, margin_factor=30, inner_padding=8,
        labels=False, value_axis=True, gridlines=True))

    v.append(textbox("trendNote", M_LEFT, 542, span(3), 34, [
        {"text": "September alone carries 19.0% of the year.  ", "size": 9, "family": UI_SB, "color": BRASS},
        {"text": "Obligations hold at $45-65bn a month for eleven months, then the use-it-or-lose-it "
                 "deadline lands $150.4bn in the final month. Two thirds of the year's dollars "
                 "(66.9%) were competed.", "size": 9, "family": UI, "color": TEXT2}]))

    v.append(rect("rowRule", M_LEFT, 584, CONTENT_W, 1, HAIRLINE, z=1))

    # -- supporting analysis ------------------------------------------------
    v.append(barchart(
        "sizeBands", M_LEFT, 600, span(2), 268,
        category=cproj("DimActionSize", "Action Size Band"),
        values=[mproj("Obligations")],
        title="HOW OBLIGATED DOLLARS SPLIT BY SIZE OF A SINGLE ACTION",
        sort_field=column("DimActionSize", "Action Size Sort"), sort_dir="Descending",
        cat_size=9, margin_factor=34, inner_padding=12,
        filters=exclude_filter("sizeBandExclude", "DimActionSize", "Action Size Band",
                                ["De-obligation (negative)", "Zero dollar"])))

    v.append(barchart(
        "topParents", colx(2), 600, span(2), 268,
        category=cproj("DimRecipient", "Parent Company"),
        values=[mproj("Obligations " + MIDDOT + " Top 8 Parents")],
        title="LARGEST PARENT COMPANIES",
        sort_field=measure("Obligations " + MIDDOT + " Top 8 Parents"),
        fill=STEEL, cat_size=9, margin_factor=60, label_precision=1, inner_padding=12))

    v.append(rect("footRule", M_LEFT, 876, CONTENT_W, 1, HAIRLINE, z=1))
    v.append(footer(y=882))

    pg, _ = page("p01Executive", "Executive brief", v)
    return pg, v


