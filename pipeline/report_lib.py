"""Helpers for generating a PBIR report definition (Power BI enhanced report format)."""
import json, os, shutil

# ---------------------------------------------------------------- design tokens
BG        = "#0D0F12"
SURFACE   = "#14171C"
ELEVATED  = "#1B1F26"
HAIRLINE  = "#262B33"
TEXT      = "#E8EAED"
TEXT2     = "#9AA3AE"
MUTED     = "#5F6873"
BRASS     = "#D4A843"
STEEL     = "#6FA8C7"
SAGE      = "#8FB98A"
CLAY      = "#C77E6B"
IRIS      = "#9B8FC0"
GRAPHITE  = "#7D8894"
POSITIVE  = "#7FB069"
NEGATIVE  = "#C25B4E"

SERIF = "Georgia"
UI    = "Segoe UI"
UI_L  = "Segoe UI Light"
UI_SB = "Segoe UI Semibold"
MONO  = "Consolas"

PAGE_W, PAGE_H = 1440, 900
RAIL_W = 212
M_LEFT = 244          # content left margin
M_RIGHT = 1408        # content right edge
CONTENT_W = M_RIGHT - M_LEFT           # 1176
COL_W = 279
GUTTER = 16
def colx(i):          # macro column x position, i in 0..3
    return M_LEFT + i * (COL_W + GUTTER)
def span(n):          # width of n macro columns
    return n * COL_W + (n - 1) * GUTTER

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json"
SCHEMA_PAGE   = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_PAGES  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
SCHEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json"
SCHEMA_VER    = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"
SCHEMA_PBIR   = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"
SCHEMA_BOOKMARK  = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/2.1.0/schema.json"
SCHEMA_BOOKMARKS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json"

# ---------------------------------------------------------------- expressions
def lit(value):                       return {"expr": {"Literal": {"Value": value}}}
def s(text):                          return lit("'" + str(text).replace("'", "''") + "'")
def d(number):                        return lit(f"{number}D")
def i(number):                        return lit(f"{number}L")
def b(flag):                          return lit("true" if flag else "false")
def color(hex_value):                 return {"solid": {"color": lit("'" + hex_value + "'")}}

def measure(name, table="Metrics"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}
def column(table, name):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}

def proj(field, qref, display=None, fmt=None):
    p = {"field": field, "queryRef": qref, "nativeQueryRef": qref.split(".")[-1]}
    if display: p["displayName"] = display
    if fmt:     p["format"] = fmt
    return p

def mproj(name, table="Metrics", display=None, fmt=None):
    return proj(measure(name, table), f"{table}.{name}", display, fmt)
def cproj(table, name, display=None, fmt=None):
    return proj(column(table, name), f"{table}.{name}", display, fmt)

def sort_by(field, direction="Descending", default=True):
    return {"sort": [{"field": field, "direction": direction}], "isDefaultSort": default}

# ---------------------------------------------------------------- visual container
def container(name, x, y, w, h, z=0, tab=None):
    pos = {"x": x, "y": y, "width": w, "height": h, "z": z}
    if tab is not None: pos["tabOrder"] = tab
    return {"$schema": SCHEMA_VISUAL, "name": name, "position": pos}

def vtitle(text, size=10, family=UI_SB, fcolor=TEXT2, align="left", show=True):
    return [{"properties": {
        "show": b(show), "text": s(text), "fontFamily": s(family),
        "fontSize": d(size), "fontColor": color(fcolor), "alignment": s(align),
        "titleWrap": b(False), "background": color("#00000000")}}]

NO_HEADER = [{"properties": {
    "show": b(True), "transparency": d(100),
    "showVisualInformationButton": b(False), "showVisualWarningButton": b(False),
    "showVisualErrorButton": b(False), "showDrillUpButton": b(False),
    "showDrillDownLevelButton": b(False), "showDrillDownExpandButton": b(False),
    "showDrillToggleButton": b(False), "showPinButton": b(False),
    "showFilterRestatementButton": b(False), "showFocusModeButton": b(False),
    "showCopyVisualImageButton": b(False), "showSeeDataLayoutToggleButton": b(False),
    "showOptionsMenu": b(False), "showCommentButton": b(False),
    "showTooltipButton": b(False), "showSmartNarrativeButton": b(False),
    "showPersonalizeVisualButton": b(False)}}]

def vco(title=None, subtitle=None, background=None, border=False, padding=None):
    """visualContainerObjects"""
    out = {"visualHeader": NO_HEADER}
    if title is not None:
        out["title"] = title
    else:
        out["title"] = [{"properties": {"show": b(False)}}]
    if subtitle is not None:
        out["subTitle"] = subtitle
    else:
        out["subTitle"] = [{"properties": {"show": b(False)}}]
    if background:
        out["background"] = [{"properties": {"show": b(True), "color": color(background), "transparency": d(0)}}]
    else:
        out["background"] = [{"properties": {"show": b(False)}}]
    out["border"] = [{"properties": {"show": b(bool(border))}}]
    out["dropShadow"] = [{"properties": {"show": b(False)}}]
    if padding:
        out["padding"] = [{"properties": {k: d(v) for k, v in padding.items()}}]
    return out


def exclude_filter(fname, table, col, values):
    """Visual-level filter that removes specific category members."""
    # NOTE: the published filterConfiguration schema marks $schema as required, but
    # Power BI Desktop rejects it on an INLINE visual filterConfig ("An additional
    # property '$schema' was included"). Desktop's behaviour is authoritative here.
    return {
        "filters": [{
            "name": fname,
            "field": column(table, col),
            "type": "Categorical",
            "filter": {
                "Version": 2,
                "From": [{"Name": "t", "Entity": table, "Type": 0}],
                "Where": [{
                    "Condition": {
                        "Not": {
                            "Expression": {
                                "In": {
                                    "Expressions": [{"Column": {
                                        "Expression": {"SourceRef": {"Source": "t"}},
                                        "Property": col}}],
                                    "Values": [[{"Literal": {"Value": "'" + x.replace("'", "''") + "'"}}]
                                                for x in values],
                                }
                            }
                        }
                    }
                }],
            },
            "howCreated": "User",
        }]
    }


# ---------------------------------------------------------------- visual builders
def textbox(name, x, y, w, h, runs, align="left", z=0, valign="top"):
    """runs: list of dicts {text, size, family, color, bold, italic}"""
    text_runs = []
    for r in runs:
        style = {"fontSize": f"{r.get('size',11)}pt",
                 "fontFamily": r.get("family", UI),
                 "color": r.get("color", TEXT)}
        if r.get("bold"):   style["fontWeight"] = "bold"
        if r.get("italic"): style["fontStyle"] = "italic"
        if r.get("spacing") is not None: style["letterSpacing"] = r["spacing"]
        text_runs.append({"value": r["text"], "textStyle": style})
    v = container(name, x, y, w, h, z)
    v["visual"] = {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {
            "paragraphs": [{"textRuns": text_runs, "horizontalTextAlignment": align}],
            "verticalContentAlignment": s(valign)}}]},
        "visualContainerObjects": vco(),
        "drillFilterOtherVisuals": True,
    }
    return v

def rect(name, x, y, w, h, fill, z=-1, transparency=0):
    """Filled rectangle. Shape formatting is state-scoped in this Power BI build, so the
    colour properties carry {"selector": {"id": "default"}} - without it Power BI keeps
    the stock blue shape fill."""
    v = container(name, x, y, w, h, z)
    v["visual"] = {
        "visualType": "shape",
        "objects": {
            "shape": [{"properties": {"tileShape": s("rectangle")},
                        "selector": {"id": "default"}}],
            "fill": [{"properties": {"show": b(True)}},
                      {"properties": {"fillColor": color(fill), "transparency": d(transparency)},
                       "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": b(False)}},
                         {"properties": {"show": b(False), "transparency": d(100)},
                          "selector": {"id": "default"}}],
        },
        "visualContainerObjects": vco(),
        "drillFilterOtherVisuals": True,
    }
    return v


def hairline(name, x, y, w, color_hex=HAIRLINE, thickness=1):
    return rect(name, x, y, w, thickness, color_hex, z=1)

def card(name, x, y, w, h, meas, units=0, precision=0, value_size=28,
         value_color=TEXT, align="left"):
    """KPI value only. The label and context line are separate textboxes so the
    value never competes with them for the card's vertical space."""
    v = container(name, x, y, w, h)
    v["visual"] = {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [mproj(meas)]}}},
        "objects": {
            "labels": [{"properties": {
                "color": color(value_color), "fontFamily": s(UI_L), "fontSize": d(value_size),
                "labelDisplayUnits": d(units), "labelPrecision": d(precision),
                "horizontalAlignment": s(align)}}],
            "categoryLabels": [{"properties": {"show": b(False)}}],
            "wordWrap": [{"properties": {"show": b(False)}}],
        },
        "visualContainerObjects": vco(),
        "drillFilterOtherVisuals": True,
    }
    return v


def _axis(show=True, title=False, size=9, label_color=TEXT2, gridlines=False,
          grid_color=HAIRLINE, units=None, precision=None, margin_factor=None,
          concat=None, inner_padding=None):
    p = {"show": b(show), "showAxisTitle": b(title), "fontFamily": s(UI), "fontSize": d(size),
         "labelColor": color(label_color), "gridlineShow": b(gridlines)}
    if gridlines:
        p["gridlineColor"] = color(grid_color); p["gridlineThickness"] = d(1)
        p["gridlineStyle"] = s("solid")
    if units is not None:     p["labelDisplayUnits"] = d(units)
    if precision is not None: p["labelPrecision"] = d(precision)
    if margin_factor is not None: p["maxMarginFactor"] = d(margin_factor)
    if concat is not None:    p["concatenateLabels"] = b(concat)
    if inner_padding is not None: p["innerPadding"] = d(inner_padding)
    return [{"properties": p}]


def barchart(name, x, y, w, h, category, values, title=None, fill=BRASS,
             labels=True, label_units=1000000000, label_precision=1,
             sort_field=None, sort_dir="Descending", cat_size=10, cat_color=TEXT,
             value_axis=False, series=None, visual_type="barChart", label_color=TEXT2,
             data_colors=None, legend=False, tooltip_page=None, margin_factor=45,
             axis_units=1000000000, axis_precision=0, gridlines=False,
             inner_padding=14, label_position=None, filters=None):
    v = container(name, x, y, w, h)
    qs = {"Category": {"projections": [category]}, "Y": {"projections": values}}
    if series: qs["Series"] = {"projections": [series]}
    query = {"queryState": qs}
    if sort_field is not None:
        query["sortDefinition"] = sort_by(sort_field, sort_dir)
    objects = {
        "categoryAxis": _axis(True, False, cat_size, cat_color, False,
                               margin_factor=margin_factor, concat=False,
                               inner_padding=inner_padding),
        "valueAxis":    _axis(value_axis, False, 9, MUTED, gridlines,
                               units=axis_units, precision=axis_precision),
        "legend":       [{"properties": {"show": b(legend), "position": s("TopLeft"),
                                          "showTitle": b(False), "fontFamily": s(UI),
                                          "fontSize": d(9), "labelColor": color(TEXT2)}}],
        "labels":       [{"properties": {"show": b(labels), "fontFamily": s(UI), "fontSize": d(9),
                                          "color": color(label_color),
                                          "labelDisplayUnits": d(label_units),
                                          "labelPrecision": d(label_precision),
                                          "labelOverflow": b(True)}}],
        "plotArea":     [{"properties": {"transparency": d(100)}}],
        "dataPoint":    data_colors or [{"properties": {"fill": color(fill)}}],
    }
    if label_position:
        objects["labels"][0]["properties"]["labelPosition"] = s(label_position)
    vis = {"visualType": visual_type, "query": query, "objects": objects,
           "visualContainerObjects": vco(title=vtitle(title) if title else None),
           "drillFilterOtherVisuals": True}
    if tooltip_page:
        vis["visualContainerObjects"]["visualTooltip"] = [{"properties": {
            "show": b(True), "type": s("ReportPage"), "section": s(tooltip_page)}}]
    v["visual"] = vis
    if filters:
        v["filterConfig"] = filters
    return v


def columnchart(name, x, y, w, h, category, values, title=None, fill=BRASS,
                sort_field=None, sort_dir="Ascending", labels=False,
                label_units=1000000000, label_precision=0, axis_units=1000000000,
                cat_size=9, data_colors=None):
    v = container(name, x, y, w, h)
    query = {"queryState": {"Category": {"projections": [category]},
                             "Y": {"projections": values}}}
    if sort_field is not None:
        query["sortDefinition"] = sort_by(sort_field, sort_dir)
    v["visual"] = {
        "visualType": "columnChart",
        "query": query,
        "objects": {
            "categoryAxis": _axis(True, False, cat_size, TEXT2, False, concat=False),
            "valueAxis":    _axis(True, False, 9, MUTED, True, units=axis_units, precision=0),
            "legend":       [{"properties": {"show": b(False)}}],
            "labels":       [{"properties": {"show": b(labels), "fontFamily": s(UI), "fontSize": d(9),
                                              "color": color(TEXT2),
                                              "labelDisplayUnits": d(label_units),
                                              "labelPrecision": d(label_precision)}}],
            "plotArea":     [{"properties": {"transparency": d(100)}}],
            "dataPoint":    data_colors or [{"properties": {"fill": color(fill)}}],
        },
        "visualContainerObjects": vco(title=vtitle(title) if title else None),
        "drillFilterOtherVisuals": True,
    }
    return v


def linechart(name, x, y, w, h, category, values, title=None, fill=BRASS,
              sort_field=None, sort_dir="Ascending", series=None, legend=False):
    v = container(name, x, y, w, h)
    qs = {"Category": {"projections": [category]}, "Y": {"projections": values}}
    if series: qs["Series"] = {"projections": [series]}
    query = {"queryState": qs}
    if sort_field is not None:
        query["sortDefinition"] = sort_by(sort_field, sort_dir)
    v["visual"] = {
        "visualType": "lineChart",
        "query": query,
        "objects": {
            "categoryAxis": _axis(True, False, 9, TEXT2, False),
            "valueAxis":    _axis(True, False, 9, MUTED, True),
            "legend":       [{"properties": {"show": b(legend), "position": s("TopLeft"), "showTitle": b(False),
                                              "fontFamily": s(UI), "fontSize": d(9), "labelColor": color(TEXT2)}}],
            "labels":       [{"properties": {"show": b(False)}}],
            "dataPoint":    [{"properties": {"fill": color(fill)}}],
            "lineStyles":   [{"properties": {"strokeWidth": d(2), "showMarker": b(False)}}],
            "plotArea":     [{"properties": {"transparency": d(100)}}],
        },
        "visualContainerObjects": vco(title=vtitle(title) if title else None),
        "drillFilterOtherVisuals": True,
    }
    return v

def table(name, x, y, w, h, projections, title=None, sort_field=None, sort_dir="Descending",
          value_size=10, header_size=9, row_padding=6, tooltip_page=None, filters=None):
    v = container(name, x, y, w, h)
    query = {"queryState": {"Values": {"projections": projections}}}
    if sort_field is not None:
        query["sortDefinition"] = sort_by(sort_field, sort_dir)
    vis = {
        "visualType": "tableEx",
        "query": query,
        "objects": {
            "grid": [{"properties": {
                "gridVertical": b(False), "gridHorizontal": b(True),
                "gridHorizontalColor": color(HAIRLINE), "gridHorizontalWeight": d(1),
                "outlineColor": color(HAIRLINE), "outlineWeight": d(1), "rowPadding": d(row_padding),
                "textSize": d(value_size)}}],
            "columnHeaders": [{"properties": {
                "fontFamily": s(UI_SB), "fontSize": d(header_size), "fontColor": color(MUTED),
                "backColor": color(BG), "outline": s("BottomOnly"), "alignment": s("Left"),
                "wordWrap": b(False)}}],
            "values": [{"properties": {
                "fontFamily": s(UI), "fontSize": d(value_size), "fontColor": color(TEXT),
                "backColor": color(BG), "backColorSecondary": color(BG),
                "outline": s("None"), "urlIcon": b(True)}}],
            "total": [{"properties": {"totals": b(False)}}],
        },
        "visualContainerObjects": vco(title=vtitle(title) if title else None),
        "drillFilterOtherVisuals": True,
    }
    if tooltip_page:
        vis["visualContainerObjects"]["visualTooltip"] = [{"properties": {
            "show": b(True), "type": s("ReportPage"), "section": s(tooltip_page)}}]
    v["visual"] = vis
    if filters:
        v["filterConfig"] = filters
    return v

def matrix(name, x, y, w, h, rows, columns, values, title=None, row_subtotals=False,
           column_subtotals=False, value_size=10):
    v = container(name, x, y, w, h)
    v["visual"] = {
        "visualType": "pivotTable",
        "query": {"queryState": {
            "Rows": {"projections": rows},
            "Columns": {"projections": columns},
            "Values": {"projections": values}}},
        "objects": {
            "grid": [{"properties": {
                "gridVertical": b(False), "gridHorizontal": b(True),
                "gridHorizontalColor": color(HAIRLINE), "outlineColor": color(HAIRLINE),
                "rowPadding": d(6), "textSize": d(value_size)}}],
            "columnHeaders": [{"properties": {
                "fontFamily": s(UI_SB), "fontSize": d(9), "fontColor": color(MUTED),
                "backColor": color(BG), "outline": s("BottomOnly"), "wordWrap": b(False)}}],
            "rowHeaders": [{"properties": {
                "fontFamily": s(UI), "fontSize": d(value_size), "fontColor": color(TEXT),
                "backColor": color(BG), "outline": s("None"), "stepped": b(False)}}],
            "values": [{"properties": {
                "fontFamily": s(UI), "fontSize": d(value_size), "fontColor": color(TEXT),
                "backColor": color(BG), "backColorSecondary": color(BG)}}],
            "subTotals": [{"properties": {
                "rowSubtotals": b(row_subtotals), "columnSubtotals": b(column_subtotals)}}],
        },
        "visualContainerObjects": vco(title=vtitle(title) if title else None),
        "drillFilterOtherVisuals": True,
    }
    return v

def slicer(name, x, y, w, h, field, title=None, mode="Basic", sync_group=None,
           single_select=False, orientation="vertical"):
    v = container(name, x, y, w, h)
    objects = {
        "general": [{"properties": {"orientation": s(orientation),
                                     "outlineColor": color(HAIRLINE), "outlineWeight": d(1)}}],
        "header":  [{"properties": {"show": b(bool(title)), "text": s(title or ""),
                                     "fontFamily": s(UI_SB), "fontSize": d(9),
                                     "fontColor": color(MUTED), "outline": s("None"),
                                     "background": color("#00000000")}}],
        "items":   [{"properties": {"fontFamily": s(UI), "fontSize": d(10),
                                     "fontColor": color(TEXT2),
                                     "background": color(SURFACE),
                                     "outline": s("None")}}],
        "data":    [{"properties": {"mode": s("Basic")}}],
        "selection": [{"properties": {"selectAllCheckboxEnabled": b(False),
                                       "singleSelect": b(single_select)}}],
    }
    vis = {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [field]}}},
        "objects": objects,
        "visualContainerObjects": vco(),
        "drillFilterOtherVisuals": True,
    }
    if sync_group:
        vis["syncGroup"] = {"groupName": sync_group, "fieldChanges": False,
                            "filterChanges": True}
    v["visual"] = vis
    return v

def page_nav(name, x, y, w, h, show_hidden=False):
    v = container(name, x, y, w, h)
    v["visual"] = {
        "visualType": "pageNavigator",
        "objects": {
            "pageNavigatorSettings": [{"properties": {
                "showPageName": b(True), "showHiddenPages": b(show_hidden),
                "gridLayout": s("vertical")}}],
            "shape": [{"properties": {"tileShape": s("rectangle"), "roundedCornerRadius": d(0),
                                       "shapeCustomRotation": d(0)}}],
            "fill":  [{"properties": {"show": b(False)}}],
            "text":  [{"properties": {"show": b(True), "fontFamily": s(UI), "fontSize": d(10),
                                       "fontColor": color(TEXT2), "horizontalAlignment": s("left"),
                                       "padding": d(6)}}],
            "outline": [{"properties": {"show": b(False)}}],
        },
        "visualContainerObjects": vco(),
        "drillFilterOtherVisuals": True,
    }
    return v

def nav_button(name, x, y, w, h, text, target_page, active=False):
    """Editorial contents entry.

    Power BI stores button formatting per visual STATE. Properties without
    {"selector": {"id": "default"}} are discarded and the button falls back to the
    stock blue style - which is exactly what happened on the first build.
    """
    fg = TEXT if active else TEXT2
    bgc = ELEVATED if active else SURFACE
    v = container(name, x, y, w, h)
    v["visual"] = {
        "visualType": "actionButton",
        "objects": {
            "icon": [{"properties": {"shapeType": s("blank")}, "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": b(False)}},
                         {"properties": {"show": b(False)}, "selector": {"id": "default"}}],
            "fill": [{"properties": {"show": b(True)}},
                      {"properties": {"fillColor": color(bgc), "transparency": d(0)},
                       "selector": {"id": "default"}},
                      {"properties": {"fillColor": color(ELEVATED), "transparency": d(0)},
                       "selector": {"id": "hover"}}],
            "text": [{"properties": {"show": b(True)}},
                      {"properties": {"text": s(text), "fontFamily": s(UI),
                                      "fontSize": d(10), "fontColor": color(fg),
                                      "bold": b(active),
                                      "horizontalAlignment": s("left"),
                                      "verticalAlignment": s("middle"),
                                      "leftMargin": d(28)},
                       "selector": {"id": "default"}},
                      {"properties": {"fontColor": color(TEXT)}, "selector": {"id": "hover"}}],
        },
        "visualContainerObjects": dict(vco(), visualLink=[{"properties": {
            "show": b(True), "type": s("PageNavigation"),
            "navigationSection": s(target_page), "tooltip": s(text)}}]),
        "drillFilterOtherVisuals": True,
    }
    return v

def action_button(name, x, y, w, h, text, link_type="Back", target=None, bookmark=None,
                  fill=ELEVATED, text_color=TEXT, size=9, outline=True):
    """Same object structure as nav_button, which is the structure Power BI Desktop itself
    writes. Every state-scoped property carries {"selector": {"id": "default"}}."""
    v = container(name, x, y, w, h)
    objects = {
        "icon": [{"properties": {"shapeType": s("blank")}, "selector": {"id": "default"}}],
        "outline": [{"properties": {"show": b(outline)}},
                     {"properties": {"lineColor": color(HAIRLINE), "weight": d(1),
                                      "transparency": d(0)},
                      "selector": {"id": "default"}}],
        "fill": [{"properties": {"show": b(True)}},
                  {"properties": {"fillColor": color(fill), "transparency": d(0)},
                   "selector": {"id": "default"}},
                  {"properties": {"fillColor": color(BRASS), "transparency": d(0)},
                   "selector": {"id": "hover"}}],
        "text": [{"properties": {"show": b(True)}},
                  {"properties": {"text": s(text), "fontFamily": s(UI_SB), "fontSize": d(size),
                                   "fontColor": color(text_color),
                                   "horizontalAlignment": s("center"),
                                   "verticalAlignment": s("middle")},
                   "selector": {"id": "default"}},
                  {"properties": {"fontColor": color(BG)}, "selector": {"id": "hover"}}],
    }
    link = {"show": b(True), "type": s(link_type)}
    if target:   link["navigationSection"] = s(target)
    if bookmark: link["bookmark"] = s(bookmark)
    v["visual"] = {
        "visualType": "actionButton",
        "objects": objects,
        "visualContainerObjects": dict(vco(), visualLink=[{"properties": link}]),
        "drillFilterOtherVisuals": True,
    }
    return v


# ---------------------------------------------------------------- page
def page(name, display_name, visuals, width=PAGE_W, height=PAGE_H,
         binding=None, visibility=None, interactions=None, filters=None, page_type=None):
    p = {
        "$schema": SCHEMA_PAGE,
        "name": name,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "width": width,
        "height": height,
        "objects": {
            "background": [{"properties": {"color": color(BG), "transparency": d(0)}}],
            "outspace":   [{"properties": {"color": color(BG), "transparency": d(0)}}],
            "displayArea":[{"properties": {"verticalAlignment": s("Top")}}],
        },
    }
    if page_type:    p["type"] = page_type
    if binding:      p["pageBinding"] = binding
    if visibility:   p["visibility"] = visibility
    if interactions: p["visualInteractions"] = interactions
    if filters:      p["filterConfig"] = filters
    return p, visuals

# ---------------------------------------------------------------- writer
def write_report(root, pages, page_order, active_page, theme_path=None, bookmarks=None):
    definition = os.path.join(root, "definition")
    if os.path.exists(definition):
        shutil.rmtree(definition)
    os.makedirs(os.path.join(definition, "pages"), exist_ok=True)

    def dump(path, obj):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    dump(os.path.join(definition, "version.json"), {"$schema": SCHEMA_VER, "version": "2.0.0"})

    base_import = {"visual": "2.12.0", "report": "3.3.0", "page": "2.1.0"}
    report = {
        "$schema": SCHEMA_REPORT,
        "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU09",
                                            "reportVersionAtImport": base_import,
                                            "type": "SharedResources"}},
        "objects": {
            "outspacePane": [{"properties": {"expanded": b(False), "visible": b(True)}}],
        },
        "settings": {"useStylableVisualContainerHeader": True,
                      "defaultFilterActionIsDataFilter": True,
                      "useDefaultAggregateDisplayName": True},
    }
    report["resourcePackages"] = [{
        "name": "SharedResources", "type": "SharedResources",
        "items": [{"name": "Fluent2-CY26SU09", "path": "BaseThemes/Fluent2-CY26SU09.json",
                    "type": "BaseTheme"}]}]
    if theme_path:
        # the customTheme name must match the RegisteredResources item name exactly,
        # extension included - otherwise Power BI silently falls back to the base theme
        report["themeCollection"]["customTheme"] = {
            "name": "FederalLedger.json", "reportVersionAtImport": base_import,
            "type": "RegisteredResources"}
        report["resourcePackages"].append({
            "name": "RegisteredResources", "type": "RegisteredResources",
            "items": [{"name": "FederalLedger.json", "path": "FederalLedger.json",
                        "type": "CustomTheme"}]})
    dump(os.path.join(definition, "report.json"), report)

    dump(os.path.join(definition, "pages", "pages.json"),
         {"$schema": SCHEMA_PAGES, "pageOrder": page_order, "activePageName": active_page})

    for (pg, visuals) in pages:
        pdir = os.path.join(definition, "pages", pg["name"])
        os.makedirs(os.path.join(pdir, "visuals"), exist_ok=True)
        dump(os.path.join(pdir, "page.json"), pg)
        for v in visuals:
            vdir = os.path.join(pdir, "visuals", v["name"])
            os.makedirs(vdir, exist_ok=True)
            dump(os.path.join(vdir, "visual.json"), v)

    if bookmarks:
        bdir = os.path.join(definition, "bookmarks")
        os.makedirs(bdir, exist_ok=True)
        names = []
        for bm in bookmarks:
            dump(os.path.join(bdir, bm["name"] + ".bookmark.json"), bm)
            names.append(bm["name"])
        dump(os.path.join(bdir, "bookmarks.json"),
             {"$schema": SCHEMA_BOOKMARKS, "items": [{"name": n} for n in names]})

    return definition

def stacked_column(name, x, y, w, h, category, values, series, title=None,
                   sort_field=None, sort_dir="Ascending", axis_units=1000000000,
                   cat_size=9, palette=None, legend=True):
    """Monthly composition. Series colours come from the theme's dataColors unless a
    palette of {"properties": {...}, "selector": {...}} entries is supplied."""
    v = container(name, x, y, w, h)
    query = {"queryState": {"Category": {"projections": [category]},
                             "Y": {"projections": values},
                             "Series": {"projections": [series]}}}
    if sort_field is not None:
        query["sortDefinition"] = sort_by(sort_field, sort_dir)
    v["visual"] = {
        "visualType": "columnChart",   # built-in stacked column; "stackedColumnChart" is not a valid type name
        "query": query,
        "objects": {
            "categoryAxis": _axis(True, False, cat_size, TEXT2, False, concat=False),
            "valueAxis":    _axis(True, False, 9, MUTED, True, units=axis_units, precision=0),
            "legend":       [{"properties": {"show": b(legend), "position": s("Top"),
                                              "showTitle": b(False), "fontFamily": s(UI),
                                              "fontSize": d(9), "labelColor": color(TEXT2)}}],
            "labels":       [{"properties": {"show": b(False)}}],
            "plotArea":     [{"properties": {"transparency": d(100)}}],
        },
        "visualContainerObjects": vco(title=vtitle(title) if title else None),
        "drillFilterOtherVisuals": True,
    }
    if palette:
        v["visual"]["objects"]["dataPoint"] = palette
    return v


def filled_map(name, x, y, w, h, location, values, title=None, tooltip_page=None):
    v = container(name, x, y, w, h)
    vis = {
        "visualType": "filledMap",
        "query": {"queryState": {"Category": {"projections": [location]},
                                  "Y": {"projections": values}}},
        "objects": {
            "mapStyles": [{"properties": {"mapTheme": s("dark")}}],
            "legend":    [{"properties": {"show": b(False)}}],
            "dataPoint": [{"properties": {"fillRule": {"linearGradient2": {
                "min": {"color": color(SURFACE)}, "max": {"color": color(BRASS)}}}}}],
        },
        "visualContainerObjects": vco(title=vtitle(title) if title else None),
        "drillFilterOtherVisuals": True,
    }
    if tooltip_page:
        vis["visualContainerObjects"]["visualTooltip"] = [{"properties": {
            "show": b(True), "type": s("ReportPage"), "section": s(tooltip_page)}}]
    v["visual"] = vis
    return v


def drillthrough_filter(fname, table, col):
    """Empty categorical filter that a drillthrough binding fills in at click time."""
    return {"name": fname, "field": column(table, col), "type": "Categorical",
            "howCreated": "Drillthrough", "isHiddenInViewMode": False}


def drillthrough_binding(bname, params):
    """params: list of (paramName, filterName, table, col)."""
    return {
        "name": bname,
        "type": "Drillthrough",
        "parameters": [{"name": pn, "boundFilter": fn, "fieldExpr": column(t, c)}
                        for pn, fn, t, c in params],
    }


