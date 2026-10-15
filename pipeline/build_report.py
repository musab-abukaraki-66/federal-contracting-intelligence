"""Assemble the full Project 06 PBIR report definition."""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_lib import *                    # noqa
from build_report_head import (page01, PBIP_ROOT, REPORT_DIR, MODEL_DIR,
                               THEME_SRC, BASE_THEME)                 # noqa
from pages_02_07 import (page02, page03, page04, page05, page06, page07, page08,
                         tooltip_recipient, tooltip_agency)           # noqa


def write_wrappers():
    os.makedirs(REPORT_DIR, exist_ok=True)

    def dump(path, obj):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    dump(os.path.join(PBIP_ROOT, "FederalContracting.pbip"), {
        "version": "1.0",
        "artifacts": [{"report": {"path": "FederalContracting.Report"}}],
        "settings": {"enableAutoRecovery": True}})

    dump(os.path.join(MODEL_DIR, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "FederalContracting"},
        "config": {"version": "2.0", "logicalId": "7c1f2a90-0c3b-4c7e-9d21-2f6a51b0e401"}})
    dump(os.path.join(MODEL_DIR, "definition.pbism"), {"version": "4.2", "settings": {}})

    dump(os.path.join(REPORT_DIR, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "Federal Contracting Intelligence"},
        "config": {"version": "2.0", "logicalId": "a38d5b64-4f1e-49f2-8c0a-9d7e2b1c6f33"}})
    dump(os.path.join(REPORT_DIR, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": "../FederalContracting.SemanticModel"}}})

    shared = os.path.join(REPORT_DIR, "StaticResources", "SharedResources", "BaseThemes")
    os.makedirs(shared, exist_ok=True)
    shutil.copyfile(BASE_THEME, os.path.join(shared, "Fluent2-CY26SU09.json"))

    res = os.path.join(REPORT_DIR, "StaticResources", "RegisteredResources")
    os.makedirs(res, exist_ok=True)
    shutil.copyfile(THEME_SRC, os.path.join(res, "FederalLedger.json"))


def main():
    write_wrappers()
    pages = [page01(), page02(), page03(), page04(), page05(), page06(), page07(), page08(),
             tooltip_recipient(), tooltip_agency()]

    # tooltip pages must not appear in the page strip
    order = [p[0]["name"] for p in pages if not p[0]["name"].startswith("tt")]
    out = write_report(REPORT_DIR, pages, order, "p01Executive", theme_path=True)
    print("wrote %s" % out)
    for pg, vis in pages:
        print("  %-16s %-26s %3d visuals" % (pg["name"], pg["displayName"], len(vis)))
    print("  total visuals: %d" % sum(len(v) for _, v in pages))


if __name__ == "__main__":
    main()
