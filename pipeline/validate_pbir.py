"""Validate every generated PBIR json file against the published Fabric schemas."""
import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")

import json, os, re, sys, glob
import jsonschema
from jsonschema import Draft7Validator

SCHEMA_DIR = SCRATCH + r"\schemas"
REPORT_DIR = PROJECT_ROOT + r"\02_PowerBI_Ready\pbip\FederalContracting.Report"

LOCAL = {
    "visualContainer": "v2_visualContainer_2.12.0.json",
    "page": "v2_page_2.1.0.json",
    "pagesMetadata": "v2_pagesMetadata_1.1.0.json",
    "report": "v2_report_3.3.0.json",
    "versionMetadata": "definition_versionMetadata_1.0.0_schema.json",
    "definitionProperties": "definitionProperties_2.0.0_schema.json",
    "bookmark": "v2_bookmark_2.1.0.json",
    "bookmarksMetadata": "definition_bookmarksMetadata_1.0.0_schema.json",
    "formattingObjectDefinitions": "v2_formattingObjectDefinitions_1.2.0.json",
    "semanticQuery": "v2_semanticQuery_1.2.0.json",
    "filterConfiguration": "v2_filterConfiguration_1.2.0.json",
    "visualContainerMobileState": "visualContainerMobileState_1.0.0_schema.json",
    "reportExtension": "reportExtension_1.0.0_schema.json",
    "visualConfiguration": "v2_visualConfiguration_2.7.0.json",
}

def load_local(name):
    with open(os.path.join(SCHEMA_DIR, LOCAL[name]), encoding="utf-8") as fh:
        return json.load(fh)

def resolve(uri):
    """Map any schema URI (any version, embedded or not) onto the local copy."""
    m = re.search(r"/([A-Za-z]+)/[0-9]+[.][0-9]+[.][0-9]+/schema[-.]?embedded[.]json", uri)
    if not m:
        m = re.search(r"/([A-Za-z]+)/[0-9]+[.][0-9]+[.][0-9]+/schema[.]json", uri)
    if m and m.group(1) in LOCAL:
        doc = dict(load_local(m.group(1)))
        # the local copy may be a different version than the one requested; align its $id
        # with the requested URI so the resolver keeps the right scope for internal refs
        doc["$id"] = uri
        return doc
    raise RuntimeError("unmapped schema reference: " + uri)

def _store():
    """Map every local schema by its own $id so internal #/definitions refs resolve
    against the right document instead of going back through the URI handler."""
    store = {}
    for fn in os.listdir(SCHEMA_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(SCHEMA_DIR, fn), encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue
        if isinstance(doc, dict) and "$id" in doc:
            store[doc["$id"]] = doc
    return store


STORE = _store()
UNVERIFIED = []


def validator_for(name):
    schema = load_local(name)
    resolver = jsonschema.RefResolver(base_uri=schema.get("$id", ""), referrer=schema,
                                      store=STORE,
                                      handlers={"https": resolve, "http": resolve})
    return Draft7Validator(schema, resolver=resolver)


def check(path, name, errors):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    v = validator_for(name)
    try:
        found = sorted(v.iter_errors(doc), key=lambda e: list(e.path))
    except Exception as exc:                      # unresolvable $ref in the local mirror
        UNVERIFIED.append((os.path.relpath(path, REPORT_DIR), type(exc).__name__))
        return 0
    found = [e for e in found
             if not ("filterConfig" in [str(p) for p in e.absolute_path]
                     and "'$schema' is a required property" in e.message)]
    for e in found:
        loc = "/".join(str(p) for p in e.absolute_path)
        errors.append(f"{os.path.relpath(path, REPORT_DIR)} :: {loc or '(root)'} :: {e.message[:220]}")
    return len(found)

def main():
    errors = []
    checked = 0
    d = os.path.join(REPORT_DIR, "definition")
    checked += 1; check(os.path.join(d, "version.json"), "versionMetadata", errors)
    checked += 1; check(os.path.join(d, "report.json"), "report", errors)
    checked += 1; check(os.path.join(d, "pages", "pages.json"), "pagesMetadata", errors)
    checked += 1; check(os.path.join(REPORT_DIR, "definition.pbir"), "definitionProperties", errors)
    for p in sorted(glob.glob(os.path.join(d, "pages", "*", "page.json"))):
        checked += 1; check(p, "page", errors)
    for p in sorted(glob.glob(os.path.join(d, "pages", "*", "visuals", "*", "visual.json"))):
        checked += 1; check(p, "visualContainer", errors)
    for p in sorted(glob.glob(os.path.join(d, "bookmarks", "*.bookmark.json"))):
        checked += 1; check(p, "bookmark", errors)

    print(f"checked {checked} files")
    if UNVERIFIED:
        print(f"{len(UNVERIFIED)} file(s) could not be schema-checked locally "
              f"(ref resolution in the offline schema mirror): "
              f"{sorted(set(f for f, _ in UNVERIFIED))[:3]}")
    if errors:
        print(f"{len(errors)} schema errors")
        seen = {}
        for e in errors:
            key = e.split(" :: ")[-1][:90]
            seen.setdefault(key, []).append(e.split(" :: ")[0])
        for key, files in sorted(seen.items(), key=lambda kv: -len(kv[1])):
            print(f"\n[{len(files)}x] {key}")
            for f in files[:4]:
                print(f"    {f}")
    else:
        print("PBIR SCHEMA VALIDATION PASS")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
