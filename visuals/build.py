#!/usr/bin/env python3
"""build.py - slide figures for the CHNT31 talk (visuals/site/) and the documentation pages (docu/).

Twelve figures in the *-visuals house pattern (1750x1000, Fira Sans, SVG plus PNG)
and a caption page, written to visuals/site/. That folder is what the workflow
visuals-pages.yml publishes under /visuals/ on GitHub Pages. The documentation
(data model, CRM coverage, instance models, query page) is written by docu.py to
docu/, published under /docu/ by docu-pages.yml; `--only slides` or `--only docu`
builds one of the two.

Inputs are the repository's own files. Stage depths and sample values drawn by
hand in the figures are checked against the graph in check_quoted_values().

    py visuals/build.py
"""
import html
import sys
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import ImageFont
import resvg_py

VISUALS = Path(__file__).resolve().parent
REPO = VISUALS.parent
SITE, IMG = VISUALS/"site", VISUALS/"site"/"img"
sys.path.insert(0, str(REPO/"ontology"))
import geo_lod_basemap as gb  # noqa: E402

R, M = VISUALS/"fonts/FiraSans-Regular.ttf", VISUALS/"fonts/FiraSans-Medium.ttf"
LAND_WINDOW = (3, 30.5, 68.6, 57.5)
CI_TABLE = REPO/"data/raw/ci/cifindspots_part_full.csv"
CI_NOTES = REPO/"data/curated/ci_site_annotations.csv"
SISAL = REPO/"data/derived/sisal/tables"
WD1 = REPO/"data/raw/wd1"
LSF13_ENTITY = "708"


def land_rings():
    """Natural Earth land, clipped to the map window and thinned for a slide."""
    rings = []
    for ring in gb._rings_of(gb.land_path(str(REPO))):
        clipped = gb.clip_ring(ring, LAND_WINDOW)
        if clipped and len(clipped) >= 3:
            thin = gb.simplify(clipped, 0.02)
            if len(thin) >= 3:
                rings.append([(round(x, 3), round(y, 3)) for x, y in thin])
    return rings


def lsf13_d18o():
    """Depth and d18O of every measured sample of LSF13_2018."""
    import csv
    with open(SISAL/"d18o.csv", encoding="utf-8") as h:
        d18o = {r["sample_id"]: float(r["d18o_measurement"]) for r in csv.DictReader(h)}
    with open(SISAL/"sample.csv", encoding="utf-8") as h:
        return sorted((float(r["depth_sample"]), d18o[r["sample_id"]]) for r in csv.DictReader(h)
                      if r["entity_id"] == LSF13_ENTITY and r["sample_id"] in d18o)


def check_quoted_values():
    """Stop if a number drawn by hand has left the graph."""
    quoted = {
        REPO/"EPICA/rdf/epica_dome_c.ttl": [
            "Beginning of MIS 5 at 1782.26 m in the CH4 record", "Beginning of MIS 5 at 1759.64 m in the d18O record",
            "Beginning of MIS 5 at 1755.63 m in the dD record", "Beginning of MIS 5 at 1733.94 m in the dO2N2 record",
            "Beginning of MIS 5 at 1739.87 m in the dust record", "Beginning of MIS 6 at 2064.95 m in the CH4 record",
            "Beginning of MIS 4 at 1150.53 m in the CH4 record", "geolod:atDepth_m 1782.015", "geolod:measuredValue 436.30000",
            "epica:mis_membership_ch4_0371 a geolod:MISMembershipAssignment", "132.16"],
        REPO/"SISAL/rdf/sisal_v3_dating.ttl": [
            "sisal:hiatus_0420893 a geolod:GrowthHiatus", "sisal:datingpoint_012773 a strat:AgeControlPoint",
            "geolod:ageKaBP 35.022453", "geolod:ageKaBP 31.481986"],
    }
    for path, needles in quoted.items():
        text = path.read_text(encoding="utf-8")
        missing = [n for n in needles if n not in text]
        if missing:
            raise SystemExit(f"{path.name} no longer states: {missing}")
W, H = 1750, 1000
# Flo's semantic colour scheme
INST = ("#e2e8f0", "#000000", "#000000")
REAL = ("#166534", "#000000", "#ffffff")
CLS  = ("#9a3412", "#000000", "#ffffff")
TERM = ("#4c1d95", "#000000", "#ffffff")
OWL  = ("#ffffff", "#000000", "#000000")
PROP = ("#fbbf24", "#000000", "#000000")
WARM, COLD = ("url(#warm)",), ("url(#cold)",)
DARK, MUTED, LINE = "#1f1f1d", "#55544f", "#55544f"

def tw(s, size, med=False):
    # BASIC layout: raqm is not on every machine, and a width that differs
    # between Windows and Linux would show up as a diff in every figure.
    font = ImageFont.truetype(str(M if med else R), 100, layout_engine=ImageFont.Layout.BASIC)
    return round(font.getlength(s) * size / 100, 1)

class Fig:
    def __init__(s, name, title, w=W, h=H, outdir=None):
        # w, h and outdir default to the slide format; the docu figures (model_figs.py) pass their own.
        s.name, s.w, s.h, s.outdir, s.o = name, w, h, outdir, [
            f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img"><title>{escape(title)}</title>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M1 1L9 5L1 9" fill="none" stroke="{LINE}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>'
            f'<marker id="t" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="17" markerHeight="17" markerUnits="userSpaceOnUse" orient="auto"><path d="M1 1L11 6L1 11Z" fill="#ffffff" stroke="{LINE}" stroke-width="1.3" stroke-linejoin="round"/></marker>'
            '<pattern id="warm" width="14" height="14" patternUnits="userSpaceOnUse"><rect width="14" height="14" fill="#f9dfb8"/><circle cx="7" cy="7" r="1.6" fill="#d9974a"/></pattern>'
            '<pattern id="cold" width="11" height="11" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="11" height="11" fill="#cfe3f3"/><line x1="0" y1="0" x2="0" y2="11" stroke="#7fb0d6" stroke-width="2.4"/></pattern></defs>']
    def text(s, x, y, t, size=22, med=False, color=DARK, anchor="middle", maxw=None):
        if maxw and tw(t, size, med) > maxw: raise ValueError(f"{s.name}: too wide ({tw(t,size,med):.0f}>{maxw}): {t}")
        wt = ' font-weight="500"' if med else ""
        s.o.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" dominant-baseline="central" font-family="Fira Sans" font-size="{size}"{wt} fill="{color}">{escape(t)}</text>')
    def box(s, x, y, w, h, title, sub=None, st=INST, ts=23, ss=19, rx=6, dash=False):
        f, b, c = st
        ds = ' stroke-dasharray="8 6" stroke-width="2.4"' if dash else ' stroke-width="1"'
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" stroke="{b}"{ds}/>')
        cx = x+w/2
        if sub:
            s.text(cx, y+h/2-ts*.58, title, ts, True, c, maxw=w-14); s.text(cx, y+h/2+ts*.66, sub, ss, False, c, maxw=w-14)
        else: s.text(cx, y+h/2, title, ts, True, c, maxw=w-14)
    def line(s, x1, y1, x2, y2, m="a", dash=False, w=1.6, color=LINE):
        d = ' stroke-dasharray="7 6"' if dash else ""; mk = f' marker-end="url(#{m})"' if m else ""
        s.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"{d}{mk}/>')
    def path(s, d, m="a", dash=False):
        ds = ' stroke-dasharray="7 6"' if dash else ""; mk = f' marker-end="url(#{m})"' if m else ""
        s.o.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.6"{ds}{mk}/>')
    def rect(s, x, y, w, h, fill, stroke="none", rx=0, sw=1, dash=False):
        ds = ' stroke-dasharray="7 6"' if dash else ""
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{ds}/>')
    def raw(s, x): s.o.append(x)
    def legend(s, y, items, x=None):
        sizes = [34 + tw(t, 19) + 34 for _, t in items]
        x = (s.w - sum(sizes)) / 2 if x is None else x
        for (st, t), sz in zip(items, sizes):
            s.rect(x, y-11, 22, 22, st[0], "#000000", 3); s.text(x+32, y, t, 19, color=MUTED, anchor="start"); x += sz
    def save(s):
        d = s.outdir or IMG; d.mkdir(parents=True, exist_ok=True); p = d/f"{s.name}.svg"
        p.write_text("\n".join(s.o+["</svg>"])+"\n", encoding="utf-8", newline="\n")
        (d/f"{s.name}.png").write_bytes(resvg_py.svg_to_bytes(svg_path=str(p), background="#ffffff", skip_system_fonts=True, font_files=[str(R), str(M)], zoom=2.0))


def chip(f, x, y, t, size=18, anchor="middle"):
    w = tw(t, size) + 16
    x0 = x - w/2 if anchor == "middle" else x
    f.rect(x0, y-15, w, 30, PROP[0], "#000000", 4)
    f.text(x0+w/2, y, t, size, color="#000000")

def fig1():
    f = Fig("01-from-measurement-to-crm", "From a measurement to the CIDOC CRM family")
    heads = [(225, 370, "1  Measurement", "What was measured?"), (660, 400, "2  Semantic model", "What does it mean?"),
             (1085, 370, "3  CIDOC CRM", "What kind of thing is it?"), (1515, 390, "4  CRM extensions", "What does science add?")]
    for x, w, a, b in heads:
        f.text(x, 52, a, 31, True, maxw=w); f.text(x, 96, b, 22, color=MUTED, maxw=w)
    x0 = 40
    f.rect(x0, 135, 370, 735, "#f6f6f3", "#c9c7bf", 10)
    top, bot, m0, m1 = 165, 760, 100, 2064.95
    cy = lambda m: top + (m-m0)*(bot-top)/(m1-m0)
    edges = [m0, 475.94, 727.60, 993.46, 1150.53, 1782.26, 2064.95]
    for i, (u, l) in enumerate(zip(edges, edges[1:])):
        f.rect(x0+25, cy(u), 86, cy(l)-cy(u), "url(#warm)" if i % 2 == 0 else "url(#cold)", "#000000", 0, .8)
        f.text(x0+68, (cy(u)+cy(l))/2, f"MIS {i+1}", 18, True, "#000000")
    f.line(x0+25, cy(1782.26), x0+111, cy(1782.26), None, w=5, color="#1f1f1d")
    f.text(x0+237, 180, "EPICA Dome C", 24, True, maxw=230); f.text(x0+237, 212, "ice core, CH₄ record", 20, color=MUTED, maxw=230)
    y = 250
    for k, v in [("Depth", "1782.015 m"), ("CH₄", "436.3 ppbv"), ("Age", "132.16 ka"), ("Scale", "EDC2-gas"), ("Place", "Dome C")]:
        f.rect(x0+128, y, 220, 58, "#ffffff", "#c9c7bf")
        f.text(x0+138, y+29, k, 20, color=MUTED, anchor="start"); f.text(x0+339, y+29, v, 21, True, anchor="end"); y += 58
    f.path(f"M {x0+113} {cy(1782.26)} L {x0+128} {cy(1782.26)}", None)
    f.text(x0+134, cy(1782.26), "this row: 1782 m", 20, anchor="start", maxw=225)
    f.text(x0+185, 802, "One row of a published table", 22, maxw=340)
    f.text(x0+185, 838, "doi:10.1594/PANGAEA.472484", 19, color=MUTED, maxw=340)
    rs = [165, 345, 525, 705]
    # model column
    f.box(460, 155, 390, 120, "epica:obs_ch4_0371", None, INST, 25)
    f.o.pop(); f.text(655, 183, "epica:obs_ch4_0371", 25, True, "#000000", maxw=375)
    f.text(655, 216, "a geolod:IceCoreObservation", 20, color="#000000", maxw=375)
    f.text(655, 247, "436.3 ppbv at 1782.015 m", 20, color="#000000", maxw=375)
    tgt = [("epica:core_edc", "a geolod:IceCore", REAL), ("epica:property_ch4", "a geolod:ObservableProperty", INST), ("epica:site_dome_c", "a geolod:DrillingSite", INST)]
    for r, (a, b, st) in zip(rs[1:], tgt):
        f.box(500, r, 350, 100, a, b, st, 24, 20)
    f.path("M 480 275 L 480 755", None)
    for r, c in zip(rs[1:], ["sosa:hasFeatureOfInterest", "sosa:observedProperty", "crm:P7_took_place_at"]):
        f.line(480, r+50, 498, r+50, "a"); chip(f, 500, r-26, c, 18, "start")
    f.line(412, 215, 458, 215, "a")
    crm = [("E13", "Attribute Assignment"), ("E18", "Physical Thing"), ("E55", "Type"), ("E53", "Place")]
    ext = [("S4 Observation", "CRMsci"), ("A3 Stratigraphic Interface", "CRMarchaeo"), ("S9 Property Type", "CRMsci"), ("SP6 Declarative Place", "CRMgeo")]
    notes = ["the act of observing", "a surface inside the archive", "CH₄ as a measurable property", "the site's coordinates"]
    for i, r in enumerate(rs):
        f.box(915, r, 340, 100, crm[i][0], crm[i][1], CLS, 28, 22)
        f.box(1325, r, 385, 100, ext[i][0], ext[i][1], CLS, 25, 20)
        f.text(1517, r+122, notes[i], 20, color=MUTED, maxw=385)
        f.line(852, r+50, 913, r+50, "t"); f.line(1323, r+50, 1257, r+50, "t")
    f.legend(915, [(REAL, "Physical object"), (INST, "Instance in the graph"), (CLS, "Class"), (PROP, "Property")], x=560)
    f.line(1250, 915, 1298, 915, "t"); f.text(1310, 915, "is a  (rdfs:subClassOf)", 19, color=MUTED, anchor="start")
    f.legend(960, [(WARM, "Warm stage, odd MIS number"), (COLD, "Cold stage, even MIS number")], x=560)
    f.text(1250, 960, "Stage limits from the CH₄ record, EDC2-gas", 19, color=MUTED, anchor="start")
    f.save()

def fig2():
    f = Fig("02-crm-family", "geo-lod classes hang on the CIDOC CRM class tree through its extensions")
    f.rect(30, 30, 580, 905, "#fbeee8", "none", 12); f.rect(625, 30, 530, 905, "#f6f0dd", "none", 12); f.rect(1170, 30, 550, 905, "#eceff3", "none", 12)
    f.text(320, 72, "CIDOC CRM", 31, True); f.text(890, 72, "CRM extensions", 31, True); f.text(1445, 72, "geo-lod", 31, True)
    bh = 76
    def b(x, y, a, c, w=170, ss=17): f.box(x, y, w, bh, a, c, CLS, 25, ss)
    def g(x, y, a, c, w=510): f.box(x, y, w, bh, a, c, CLS, 23, 18)
    b(45, 435, "E1", "CRM Entity"); b(235, 245, "E7", "Activity"); b(235, 680, "E18", "Physical Thing")
    b(425, 245, "E13", "Attribute Assignment", 180); b(425, 575, "E26", "Physical Feature", 180)
    b(640, 135, "S4", "Observation", 160)
    b(636, 575, "S20", "Rigid Phys. Feature", 154, 16); b(808, 575, "A8", "Stratigraphic Unit", 154, 16); b(980, 575, "A3", "Strat. Interface", 154, 16)
    g(1190, 135, "PalaeoclimateObservation", "one measured value in an archive")
    g(1190, 245, "MISAttributeAssignment", "a stage boundary, on one source's authority")
    g(1190, 345, "strat:AgeControlPoint", "a dated tie point in an age model")
    g(1190, 445, "MISMembershipAssignment", "an observation falls within a stage")
    g(1190, 575, "GrowthHiatus", "nothing was deposited across this surface")
    g(1190, 680, "PalaeoclimateSample", "the physical archive")
    g(1190, 790, "IceCore", "EPICA Dome C", 245); g(1455, 790, "Speleothem", "SISAL v3", 245)
    f.path("M 235 283 L 225 283 L 225 473 L 217 473", "t"); f.path("M 235 718 L 225 718 L 225 473 L 217 473", "t")
    f.line(425, 283, 407, 283, "t")
    f.path("M 425 613 L 415 613 L 415 700 L 407 700", "t")
    f.line(636, 613, 607, 613, "t"); f.line(808, 613, 791, 613, "t"); f.line(980, 613, 963, 613, "t"); f.line(1190, 613, 1135, 613, "t")
    f.line(1190, 173, 802, 173, "t")
    f.path("M 640 173 L 618 173 L 618 283 L 607 283", "t")
    f.line(1190, 283, 607, 283, "t")
    f.path("M 1190 383 L 1172 383 L 1172 283", None); f.path("M 1190 483 L 1172 483 L 1172 383", None)
    f.line(1190, 736, 407, 736, "t")
    f.line(1312, 790, 1312, 758, "t"); f.line(1577, 790, 1577, 758, "t")
    f.line(575, 968, 623, 968, "t"); f.text(635, 968, "is a  (rdfs:subClassOf); chains shortened", 20, color=MUTED, anchor="start")
    f.save()

def fig3():
    f = Fig("03-stratigraphy-time", "One boundary on five chronologies: the beginning of MIS 5 in the EPICA Dome C core and its RDF graph")
    top, sc = 150, 7.0
    cy = lambda m: top + (m-1700)*sc
    lanes = [(1733.94, "AICC", "ice"), (1739.87, "EDC3", "ice"), (1755.63, "EDC2", "ice"), (1759.64, "AICC", "gas"), (1782.26, "EDC2", "gas")]
    cx, lw = 125, 58
    f.text(cx+lw*2.5, 42, "EPICA Dome C, 1700 to 1800 m", 26, True)
    for i, (d, n, ph) in enumerate(lanes):
        x = cx+i*lw
        f.text(x+lw/2, 92, n, 19, True); f.text(x+lw/2, 120, ph, 19, color=MUTED)
        f.rect(x, top, lw, cy(d)-top, "url(#warm)", "#000000", 0, .8)
        f.rect(x, cy(d), lw, cy(1800)-cy(d), "url(#cold)", "#000000", 0, .8)
        f.line(x, cy(d), x+lw, cy(d), None, w=5, color="#1f1f1d")
    for m in (1700, 1750, 1800):
        f.text(112, cy(m), f"{m} m", 20, color=MUTED, anchor="end")
    f.rect(cx+lw*1.2-58, (top+cy(1733.94))/2-24, 116, 48, "#ffffff", "#000000", 6, .8); f.text(cx+lw*1.2, (top+cy(1733.94))/2, "MIS 5", 28, True, "#000000")
    f.rect(cx+lw*3.8-58, cy(1792)-24, 116, 48, "#ffffff", "#000000", 6, .8); f.text(cx+lw*3.8, cy(1792), "MIS 6", 28, True, "#000000")
    a, b = cy(1733.94), cy(1782.26)
    xr = cx+5*lw
    f.line(cx+lw, a, 468, a, None, dash=True); f.line(xr+2, b, 468, b, None, dash=True)
    f.line(445, a+8, 445, b-8, None, w=1.6); f.text(457, (a+b)/2, "48.32 m", 28, True, anchor="start")
    for y, d in ((a, "1733.94 m"), (b, "1782.26 m")):
        f.box(470, y-48, 190, 96, d, "DepthPosition", INST, 26, 20)
    ex, ew, tx, tw_ = 845, 240, 1285, 425
    for y, n in ((a, "AICC2023-ice"), (b, "EDC2-gas")):
        f.box(ex, y-54, ew, 108, "E13", "MISBoundaryDepth", CLS, 28, 21)
        f.box(tx, y-54, tw_, 108, n, "temporal reference system", TERM, 28, 21)
        f.line(ex, y, 662, y); chip(f, 752, y-26, "crm:P141_assigned", 18)
        f.line(ex+ew, y, tx-2, y); chip(f, 1185, y-26, "geolod:inChronology", 18)
    m = (a+b)/2
    f.box(ex, m-58, ew, 116, "mis:MIS_5", "begins 132.2 ka BP", TERM, 28, 21)
    f.line(ex+120, a+54, ex+120, m-60); f.line(ex+120, b-54, ex+120, m+60)
    chip(f, ex+140, (a+54+m-58)/2, "crm:P140_assigned_attribute_to", 18, "start")
    chip(f, ex+140, (b-54+m+58)/2, "crm:P140_assigned_attribute_to", 18, "start")
    f.legend(915, [(WARM, "MIS 5, warm stage"), (COLD, "MIS 6, cold stage")], x=125)
    f.line(600, 915, 650, 915, None, w=5, color="#1f1f1d"); f.text(662, 915, "Beginning of MIS 5 on this chronology, interpolated", 19, color=MUTED, anchor="start")
    f.legend(960, [(INST, "Value"), (CLS, "Assignment (E13)"), (TERM, "Concept or reference system"), (PROP, "Property")], x=125)
    f.save()

def fig4():
    import csv
    f = Fig("04-measured-dated-interpreted", "One stalagmite, three kinds of statement: measured, dated, interpreted")
    Y = lambda d: 158 + 3.3*d
    st = f"M 62 {Y(230)} C 85 640 110 260 122 {Y(10)} C 132 {Y(-16)} 188 {Y(-16)} 198 {Y(10)} C 210 260 235 640 258 {Y(230)} Z"
    hy = Y(19.325)
    f.raw(f'<clipPath id="st2"><path d="{st}"/></clipPath><g clip-path="url(#st2)"><rect x="50" y="60" width="220" height="900" fill="url(#warm)"/><rect x="50" y="60" width="220" height="{hy-60}" fill="url(#cold)"/>')
    for y in range(250, 930, 62):
        f.raw(f'<path d="M 50 {y+28} Q 160 {y-28} 270 {y+28}" fill="none" stroke="#6b6a63" stroke-width="1"/>')
    f.raw(f'<rect x="50" y="{hy-3}" width="220" height="6" fill="#1f1f1d"/></g><path d="{st}" fill="none" stroke="#000000"/>')
    f.text(160, 38, "LSF13_2018", 24, True); f.text(160, 68, "stalagmite, Lapa sem fim", 18, color=MUTED)
    x0, x1, v0, v1 = 330, 770, -8, -2
    px = lambda v: x0+(v-v0)*(x1-x0)/(v1-v0)
    f.rect(x0, Y(10), x1-x0, Y(218.55)-Y(10), "#fbfbf9", "#c9c7bf")
    for v in range(-8, -1, 2):
        f.line(px(v), Y(218.55), px(v), Y(218.55)+7, None, w=1); f.text(px(v), Y(218.55)+24, f"−{-v}", 19, color=MUTED)
    f.text((x0+x1)/2, 68, "δ¹⁸O [‰ VPDB], every measured sample", 21, True)
    rows = lsf13_d18o()
    for part in ([r for r in rows if r[0] < 19.3], [r for r in rows if r[0] > 19.3]):
        f.raw('<path d="M ' + " L ".join(f"{px(b):.1f} {Y(a):.1f}" for a, b in part) + '" fill="none" stroke="#1f1f1d" stroke-width="1.6"/>')
    f.line(250, hy, x1, hy, None, w=3, color="#1f1f1d")
    pts = [(10, 30.21), (17.6, 31.48), (21.05, 35.02), (93.05, 36.06), (113.95, 37.10), (159.55, 37.60), (163.05, 38.12), (169.05, 39.03), (174.55, 39.54), (179.55, 39.70), (184.05, 39.85), (185.65, 39.48), (218.55, 40.40)]
    for d, a in pts:
        y = Y(d); f.raw(f'<polygon points="{x0-22},{y-7} {x0-22},{y+7} {x0-8},{y}" fill="#9a3412" stroke="#000000"/>')
    for d in (0, 50, 100, 150, 200):
        if d >= 10: f.text(x0+8, Y(d), f"{d} mm", 17, color=MUTED, anchor="start")
    hl = (97.95, -4.78)
    f.raw(f'<circle cx="{px(hl[1]):.1f}" cy="{Y(hl[0]):.1f}" r="8" fill="#ffffff" stroke="#000000" stroke-width="2"/>')
    # three statement cards
    cards = [(135, "Interpreted", "Nothing was deposited across this surface", "sisal:hiatus_0420893", "at 19.325 mm", "GrowthHiatus", "A3", "Stratigraphic Interface", "CRMarchaeo"),
             (405, "Dated", "U/Th, 35.02 ± 0.22 ka; 31.48 ka above the hiatus", "sisal:datingpoint_012773", "at 21.05 mm", "strat:AgeControlPoint", "E13", "Attribute Assignment", "CIDOC CRM"),
             (675, "Measured", "One isotope value at one depth", "sisal:obs_d18o_0420984", "−4.78 ‰ at 97.95 mm", "δ¹⁸O SpeleothemObservation", "S4", "Observation", "CRMsci")]
    for y, h, sub, inst, isub, cl, code, nm, fam in cards:
        f.rect(820, y-30, 900, 230, "#f6f6f3", "none", 10)
        f.text(845, y+6, h, 28, True, anchor="start"); f.text(1000, y+7, sub, 20, color=MUTED, anchor="start", maxw=700)
        f.box(845, y+55, 310, 105, inst, isub, INST, 21, 19)
        f.box(1205, y+55, 265, 105, cl.split(" ")[0] if " " in cl else cl, cl.split(" ")[1] if " " in cl else "geo-lod class", CLS, 21, 18)
        f.box(1520, y+55, 180, 105, code, nm, CLS, 25, 15.5)
        f.line(1155, y+107, 1203, y+107); chip(f, 1180, y+83, "a", 15); f.line(1470, y+107, 1518, y+107, "t")
        f.text(1610, y+178, fam, 18, color=MUTED)
    def badge(x, y, n):
        f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="#1f1f1d"/>'); f.text(x, y+.5, n, 19, True, "#ffffff")
    badge(x1+24, hy, "1"); badge(x0-40, Y(21.05)+24, "2"); badge(px(hl[1])+26, Y(hl[0]), "3")
    for n, (y, *_) in zip("123", cards): badge(1704, y+6, n)
    f.legend(965, [(COLD, "MIS 2, cold"), (WARM, "MIS 3, warm")], x=60)
    f.raw('<polygon points="400,958 400,972 414,965" fill="#9a3412" stroke="#000000"/>'); f.text(424, 965, "U/Th date", 19, color=MUTED, anchor="start")
    f.line(540, 965, 590, 965, None, w=3, color="#1f1f1d"); f.text(600, 965, "Growth hiatus", 19, color=MUTED, anchor="start")
    f.text(820, 965, "Stalagmite outline schematic; depth, δ¹⁸O and dates from SISAL v3", 19, color=MUTED, anchor="start")
    f.save()

def fig6():
    import csv, re
    f = Fig("06-ci-model", "A findspot says where, a measurement says what: from georeferenced core to Campanian Ignimbrite tephra")
    mw = 960
    lon0, lon1, lat1 = 3, 33, 56.5
    lat0 = lat1 - (lon1-lon0)*.72*H/mw
    px = lambda lon: (lon-lon0)*mw/(lon1-lon0); py = lambda lat: (lat1-lat)*H/(lat1-lat0)
    f.raw(f'<clipPath id="mp"><rect width="{mw}" height="{H}"/></clipPath><g clip-path="url(#mp)">')
    f.rect(0, 0, mw, H, "#dcebf2")
    d = " ".join("M " + " L ".join(f"{px(a):.1f} {py(b):.1f}" for a, b in r) + " Z" for r in land_rings())
    f.raw(f'<path d="{d}" fill="#f4f1e8" fill-rule="evenodd" stroke="#b9b4a8" stroke-width=".8"/>')
    for x in csv.DictReader(open(CI_TABLE, encoding="utf8")):
        lo, la = map(float, re.findall(r"-?[0-9.]+", x["wkt"].split("POINT")[1]))
        if x["id"] in ("22", "201", "202", "203", "52"): continue
        f.raw(f'<circle cx="{px(lo):.1f}" cy="{py(la):.1f}" r="4.5" fill="#ffffff" stroke="#5f5e5a" stroke-width="1.2"/>')
    sx, sy = px(14.1402), py(40.8275)
    f.raw('<polygon points="' + " ".join(f"{sx+(17 if i%2==0 else 7)*__import__('math').sin(i*3.14159265/5):.1f},{sy-(17 if i%2==0 else 7)*__import__('math').cos(i*3.14159265/5):.1f}" for i in range(10)) + '" fill="#4c1d95" stroke="#000000"/>')
    f.text(sx-24, sy+4, "Phlegraean Fields", 20, True, anchor="end")
    import math
    ax, ay = px(6.59), py(50.28); wx, wy = px(27.9021), py(44.0947)
    for x, y, t, an in ((ax, ay, "Auel and Dehner maars", "start"), (wx, wy, "Urluia", "end")):
        f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="#9a3412" stroke="#000000" stroke-width="1.5"/>')
    f.text(wx-16, wy-16, "Urluia", 21, True, anchor="end")
    f.text(16, H-22, "Modern coastline: Natural Earth", 16, color=MUTED, anchor="start")
    f.raw("</g>")
    # Eifel inset
    ix, iy, iw, ih = 22, 22, 400, 190
    la0, la1, lo0, lo1 = 50.235, 50.335, 6.44, 6.785
    qx = lambda lo: ix+(lo-lo0)*iw/(lo1-lo0); qy = lambda la: iy+(la1-la)*ih/(la1-la0)
    f.line(ix+iw/2, iy+ih, ax, ay-10, None, w=1.4, color="#1f1f1d")
    f.rect(ix, iy, iw, ih, "#ffffff", "#000000", 6, 1.2)
    f.text(ix+14, iy+24, "West Eifel maars", 20, True, anchor="start")
    def km(a, b):
        p1, p2 = math.radians(a[1]), math.radians(b[1]); dl = math.radians(b[0]-a[0])
        return 2*6371.0088*math.asin(math.sqrt(math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2))
    for lo, la, t, c, dy in ((6.5951, 50.2825, "AU3, AU4", "#9a3412", -22), (6.5066, 50.2928, "DE3", "#9a3412", -22), (6.714205, 50.271565, "WD1", "#166534", -22)):
        f.raw(f'<circle cx="{qx(lo):.1f}" cy="{qy(la):.1f}" r="10" fill="{c}" stroke="#000000" stroke-width="1.5"/>')
        f.text(qx(lo), qy(la)+dy, t, 21, True)
    f.text(ix+14, iy+ih-20, f"WD1 lies {km((6.5951,50.2825),(6.714205,50.271565)):.1f} km from Auel", 18, color=MUTED, anchor="start")
    f.legend(H-32, [], x=20)
    # model
    X, W2 = 985, 740
    f.text(X, 46, "Where: in the graph today", 28, True, anchor="start")
    f.box(X, 72, 330, 100, "ci:cisite_201", "Auel Maar AU3, a CIFindspot", INST, 23, 18)
    f.box(X+W2-250, 72, 250, 100, "POINT(6.5951 50.2825)", "fsl:high", INST, 18, 18)
    f.line(X+330, 122, X+W2-252, 122); chip(f, X+410, 96, "geo:hasGeometry", 15)
    f.text(X, 222, "What: from the paper, not yet in the graph", 28, True, anchor="start")
    bw, bh, cx1, cx2 = 315, 96, X, X+W2-315
    def nd(x, y, a, b, st): f.box(x, y, bw, bh, a, b, st, 22, 18, dash=True)
    r1, r2, r3 = 248, 396, 544
    nd(cx1, r1, "Core AU3", "102 m, Auel maar", REAL); nd(cx2, r1, "69.50–69.60 m", "strat:TephraLayer", INST)
    nd(cx2, r2, "S4 Observation", "EPMA, green clinopyroxene", CLS); nd(cx1, r2, "E13 Assignment", "matches CI at Urluia", CLS)
    nd(cx1, r3, "tephra:CI", "shared marker concept", TERM); nd(cx2, r3, "E5 Event", "CI eruption, 39.85 ± 0.14 ka", CLS)
    f.line(cx1+bw, r1+bh/2, cx2-2, r1+bh/2); f.line(cx2+bw/2, r1+bh, cx2+bw/2, r2-2); f.line(cx2, r2+bh/2, cx1+bw+2, r2+bh/2)
    f.line(cx1+bw/2, r2+bh, cx1+bw/2, r3-2); f.line(cx1+bw, r3+bh/2, cx2-2, r3+bh/2)
    chip(f, X+370, r1+22, "hosts", 14); chip(f, cx2+bw/2+58, r1+bh+26, "measured", 15); chip(f, X+370, r2+22, "supports", 14)
    chip(f, cx1+bw/2+52, r2+bh+26, "assigns", 15); chip(f, X+370, r3+22, "produced by", 14)
    f.line(cx1+bw/2, r1+bh+0, cx1+bw/2, r1+bh, None)
    f.text(X, 690, "One marker in three cores", 24, True, anchor="start")
    y = 722
    for c, d in (("AU3", "68.60–69.60 m"), ("AU4", "69.05–69.70 m"), ("DE3", "50.00–50.40 m")):
        f.text(X, y, c, 22, True, anchor="start"); f.text(X+90, y, d, 22, anchor="start"); y += 34
    f.text(X+W2, 722, "Modelled age 39,940 ± 150 yr b2k", 20, color=MUTED, anchor="end")
    f.text(X+W2, 756, "ELSA-20 chronology", 20, color=MUTED, anchor="end")
    f.text(X+W2, 790, "Schenk et al. 2024, Quaternary 7, 17", 20, color=MUTED, anchor="end")
    f.legend(868, [(REAL, "Physical object"), (INST, "Instance"), (CLS, "Class"), (TERM, "Concept"), (PROP, "Property")], x=X)
    f.rect(X, 907, 22, 22, "#ffffff", "#000000", 3, 2, True); f.text(X+32, 918, "Dashed: planned for the ELSA strand", 19, color=MUTED, anchor="start")
    f.raw(f'<circle cx="{X+11}" cy="962" r="10" fill="#166534" stroke="#000000"/>'); f.text(X+32, 962, "WD1, 220–132 ka", 19, color=MUTED, anchor="start")
    f.raw(f'<circle cx="{X+331}" cy="962" r="10" fill="#9a3412" stroke="#000000"/>'); f.text(X+352, 962, "CI in the core", 19, color=MUTED, anchor="start")
    f.save()

def fig7():
    import csv, re
    f = Fig("07-walsdorf-wd1", "Drill core WD1 from the Walsdorfer maar: lithology, tephra layers and one layer modelled in RDF")
    rows = []
    for r in list(csv.reader(open(WD1/"Table1.csv", encoding="utf8")))[1:]:
        a, b = map(float, r[0].split("–")); rows.append((a, b, r[1]))
    cls = {}
    for r in list(csv.reader(open(WD1/"Table7.csv", encoding="utf8")))[1:]:
        d = float(re.findall(r"([0-9.]+)\)", r[0])[0]); cls[d] = r[1]
    FILL = {"gyttja": "#e7d3b0", "sapropel": "#b8bcc0", "silt": "#f6efc4", "rubble": "#dfc7c0", "calcite": "#ffffff", "landslide": "#e6b8a8", "none": "#eeeeec", "other": "#d9d2c5"}
    def facies(t):
        t = t.lower()
        if "tephra" in t: return "tephra"
        for k, w in (("calcite", "calcite"), ("landslide", "landslide"), ("sapropel", "sapropel"), ("gyttja", "gyttja"), ("silt", "silt"), ("rubble", "rubble")):
            if w in t: return k
        return "none" if t.startswith("---") else "other"
    def tcol(a, b, t):
        if re.search("WDT|HBT|GLT|JWT", t): return "#9a3412"
        ps = [v for d, v in cls.items() if a < d <= b]
        return "#1f1f1d" if "P" in ps else ("#8a8a84" if ps else "#5c6f82")
    def column(x, w, y0, sc, d0, d1, tmin):
        Y = lambda d: y0+(d-d0)*sc
        for a, b, t in rows:
            if b <= d0 or a >= d1: continue
            k = facies(t); a2, b2 = max(a, d0), min(b, d1)
            if k != "tephra": f.rect(x, Y(a2), w, Y(b2)-Y(a2), FILL[k], "none")
        for a, b, t in rows:
            if b <= d0 or a >= d1: continue
            if facies(t) == "tephra":
                a2, b2 = max(a, d0), min(b, d1)
                f.rect(x, Y(a2), w, max(Y(b2)-Y(a2), tmin), tcol(a, b, t), "none")
        f.rect(x, Y(d0), w, Y(d1)-Y(d0), "none", "#000000", 0, 1)
        return Y
    Y = column(120, 130, 70, 9.7, 0, 87, 3)
    f.text(185, 40, "WD1, 87 m", 26, True)
    for d in range(0, 88, 10):
        f.line(112, Y(d), 120, Y(d), None, w=1); f.text(104, Y(d), f"{d} m", 19, color=MUTED, anchor="end")
    f.line(112, Y(87), 120, Y(87), None, w=1)
    for name, d, age in (("JWT", 12.95, "132 ka"), ("GLT", 20.20, "151 ± 11 ka"), ("HBT", 86.43, "215 ± 4 ka")):
        f.line(250, Y(d), 272, Y(d), None, w=2, color="#9a3412"); f.text(280, Y(d)-(38 if name == "HBT" else 0), f"{name}  {age}", 21, True, "#9a3412", anchor="start")
    f.text(280, Y(87)+22, "WDT  216,286 yr b2k ± 4 ka, conservative upper limit", 19, color="#9a3412", anchor="start", maxw=510)
    for d, t in ((46.1, "170–140 ka: silt–clay"), (70.07, "199–177 ka: 15 tephra layers"), (86.0, "217–199 ka: gyttja, sapropel")):
        pass
    f.text(280, Y(32), "170–140 ka", 20, anchor="start"); f.text(280, Y(32)+26, "silt–clay lamination", 18, color=MUTED, anchor="start")
    f.text(280, Y(58), "199–177 ka", 20, anchor="start"); f.text(280, Y(58)+26, "15 tephra layers", 18, color=MUTED, anchor="start")
    f.text(280, Y(77), "217–199 ka", 20, anchor="start"); f.text(280, Y(77)+26, "gyttja and sapropel", 18, color=MUTED, anchor="start")
    # zoom
    zx, zw, zy, zs = 570, 120, 434, 320
    f.path(f"M 250 {Y(85.5)} L 545 {Y(85.5)} L {zx} {zy}", None, dash=True); f.path(f"M 250 {Y(87)} L {zx} {Y(87)}", None, dash=True)
    Z = column(zx, zw, zy, zs, 85.5, 87, 3)
    f.text(zx+zw/2, zy-28, "85.5 to 87 m", 24, True)
    for d in (85.5, 86, 86.5, 87):
        f.text(zx-10, Z(d), f"{d:g}", 18, color=MUTED, anchor="end")
    hz = (Z(86.13)+Z(86.43))/2
    f.text(zx+zw+10, hz, "HBT", 22, True, "#9a3412", anchor="start")
    f.text(zx+zw+10, Z(86.75), "WDT", 22, True, "#9a3412", anchor="start")
    X, bw, bh = 800, 300, 100
    f.line(zx+zw+62, hz, X-2, 564, None, dash=True)
    def nd(x, y, a, b, st, w=bw): f.box(x, y, w, bh, a, b, st, 22, 18, dash=True)
    f.text(X, 46, "One layer as a graph", 28, True, anchor="start")
    nd(X, 514, "wd1:unit_HBT", "86.13–86.43 m, a strat:TephraLayer", INST, 400)
    nd(X, 218, "Gyttja above", "yellow and brown, 86.00–86.13 m", INST, 400)
    nd(1310, 70, "wd1:WD1", "a strat:Core, 87 m", REAL, 410)
    nd(1310, 218, "HBT", "Hüttenberg Tephra, marker concept", TERM, 410)
    nd(1310, 366, "Hüttenberg eruption", "a strat:Eruption, 215 ± 4 ka", CLS, 410)
    nd(1310, 514, "samples 36 to 38", "an:Specimen, leucite detected", INST, 410)
    f.path("M 1200 564 L 1250 564 L 1250 120 L 1308 120", "a")
    f.line(1250, 268, 1308, 268); f.line(1250, 416, 1308, 416); f.line(1200, 564, 1308, 564)
    for y, c in ((54, "strat:partOfCore"), (202, "strat:markerTephra"), (350, "strat:producedByEruption"), (498, "strat:hostsSpecimen")):
        chip(f, 1310, y, c, 15, "start")
    f.line(1000, 318, 1000, 512); chip(f, 1000, 416, "strat:meets", 15)
    f.text(X, 655, "Depth is measured, age is modelled", 24, True, anchor="start")
    f.text(X, 689, "Anchors: HBT 40Ar/39Ar at 86.43 m, GLT at 20.20 m", 20, color=MUTED, anchor="start", maxw=900)
    f.text(X, 720, "Primary tephra are isochrons; reworked layers do not date the sediment", 20, color=MUTED, anchor="start", maxw=900)
    f.text(X, 751, "Dashed: strat: classes exist in geo-lod, WD1 instances and IRIs are illustrative", 20, color=MUTED, anchor="start", maxw=900)
    f.legend(800, [(("#e7d3b0",), "Gyttja"), (("#b8bcc0",), "Sapropel"), (("#f6efc4",), "Silt–clay lamination"), (("#dfc7c0",), "Rubble"), (("#e6b8a8",), "Landslide")], x=X)
    f.legend(838, [(("#ffffff",), "Calcite"), (("#d9d2c5",), "Other"), (("#eeeeec",), "Not described")], x=X)
    f.legend(876, [(("#9a3412",), "Marker tephra"), (("#1f1f1d",), "Primary tephra"), (("#8a8a84",), "Reworked tephra"), (("#5c6f82",), "Tephra, not classified")], x=X)
    f.legend(914, [(REAL, "Physical object"), (INST, "Instance"), (CLS, "Class"), (TERM, "Concept")], x=X)
    f.text(X, 958, "Schenk et al. 2026, Quaternary 9, 67; tables CC BY 4.0, Fiona Schenk (wdt-tables)", 19, color=MUTED, anchor="start", maxw=900)
    f.save()

def fig5():
    import csv, math, re
    f = Fig("05-ci-map", "Campanian Ignimbrite findspots, with the twelve archaeological sites highlighted")
    lon0, lon1, lat0, lat1 = 3, 68.6, 30.5, 57.5
    px = lambda lon: (lon-lon0)*W/(lon1-lon0); py = lambda lat: (lat1-lat)*H/(lat1-lat0)
    f.rect(0, 0, W, H, "#dcebf2")
    d = " ".join("M " + " L ".join(f"{px(a):.1f} {py(b):.1f}" for a, b in r) + " Z" for r in land_rings())
    f.raw(f'<path d="{d}" fill="#f4f1e8" fill-rule="evenodd" stroke="#b9b4a8" stroke-width=".8"/>')
    src = (14.1402, 40.8275)
    def km(a, b):
        p1, p2 = math.radians(a[1]), math.radians(b[1]); dl = math.radians(b[0]-a[0])
        h = math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return 2*6371.0088*math.asin(math.sqrt(h))
    for rk in (500, 1000, 1500, 2000, 2500):
        pts, d = [], rk/6371.0088
        for i in range(181):
            b = math.radians(i*2); p = math.radians(src[1])
            la = math.asin(math.sin(p)*math.cos(d)+math.cos(p)*math.sin(d)*math.cos(b))
            lo = math.radians(src[0])+math.atan2(math.sin(b)*math.sin(d)*math.cos(p), math.cos(d)-math.sin(p)*math.sin(la))
            pts.append((px(math.degrees(lo)), py(math.degrees(la))))
        f.raw('<path d="M '+" L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)+' Z" fill="none" stroke="#7a8a92" stroke-width="1.2" stroke-dasharray="6 7"/>')
        x, y = pts[72]
        f.text(x+8, y-10, f"{rk} km", 18, color="#55666e", anchor="start")
    R = list(csv.DictReader(open(CI_TABLE, encoding="utf8")))
    cur = {x["ci_id"] for x in csv.DictReader(open(CI_NOTES, encoding="utf8")) if x["isArchaeologicalSite"] == "true"}
    arch = []
    for x in R:
        lo, la = map(float, re.findall(r"-?[0-9.]+", x["wkt"].split("POINT")[1]))
        if x["id"] == "22": continue
        if "ArchaeologicalSite" in x["spatialtype"] or x["id"] in cur:
            arch.append((km(src, (lo, la)), x["id"], lo, la, x["certainty"].replace("fsl:", "").strip()))
        else:
            f.raw(f'<circle cx="{px(lo):.1f}" cy="{py(la):.1f}" r="5" fill="#ffffff" stroke="#5f5e5a" stroke-width="1.2"/>')
    arch.sort()
    names = {"5": "Castelcivita Cave", "19": "Paglicci Cave", "42": "Kozarnika Cave", "43": "Temnata Cave", "44": "Toplitsa Cave",
             "45": "Franchthi Cave", "50": "Golema Pesht Cave", "51": "Crvena Stijena", "59": "Kostenki-Borshchevo",
             "62": "Tabula Traiana", "63": "Titel Plateau", "65": "Haua Fteah"}
    off = {"5": (-6, 46), "19": (-40, -46), "51": (26, -36), "50": (-48, 42), "62": (24, -48), "63": (-30, -46), "42": (-44, 40) , "43": (20, 52), "44": (56, 18)}
    s = (px(src[0]), py(src[1]))
    f.raw('<polygon points="' + " ".join(f"{s[0]+(17 if i%2==0 else 7)*math.sin(i*math.pi/5):.1f},{s[1]-(17 if i%2==0 else 7)*math.cos(i*math.pi/5):.1f}" for i in range(10)) + '" fill="#4c1d95" stroke="#000000"/>')
    for n, (k, i, lo, la, c) in enumerate(arch, 1):
        x, y = px(lo), py(la); dx, dy = off.get(i, (0, 0)); hollow = c in ("dubious", "low")
        if dx or dy:
            f.line(x, y, x+dx, y+dy, None, w=1.4, color="#1f1f1d")
            f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#1f1f1d"/>')
        fill, col = ("#ffffff", "#9a3412") if hollow else ("#9a3412", "#ffffff")
        f.raw(f'<circle cx="{x+dx:.1f}" cy="{y+dy:.1f}" r="16" fill="{fill}" stroke="#9a3412" stroke-width="2.5"/>')
        f.text(x+dx, y+dy+.5, str(n), 18, True, col)
    pw = 395; x0 = W-pw-22
    f.rect(x0, 22, pw, H-44, "#ffffff", "#c9c7bf", 10)
    f.text(x0+22, 62, "Archaeological sites", 27, True, anchor="start"); f.text(x0+22, 96, "with Campanian Ignimbrite tephra", 20, color=MUTED, anchor="start")
    y = 142
    for n, (k, i, lo, la, c) in enumerate(arch, 1):
        hollow = c in ("dubious", "low")
        fill, col = ("#ffffff", "#9a3412") if hollow else ("#9a3412", "#ffffff")
        f.raw(f'<circle cx="{x0+38}" cy="{y}" r="16" fill="{fill}" stroke="#9a3412" stroke-width="2.5"/>'); f.text(x0+38, y+.5, str(n), 18, True, col)
        f.text(x0+66, y, names[i], 21, True, anchor="start", maxw=235); f.text(x0+pw-20, y, f"{k:,.0f} km", 19, color=MUTED, anchor="end"); y += 54
    y += 2
    f.raw(f'<polygon points="' + " ".join(f"{x0+38+(14 if i%2==0 else 6)*math.sin(i*math.pi/5):.1f},{y-(14 if i%2==0 else 6)*math.cos(i*math.pi/5):.1f}" for i in range(10)) + '" fill="#4c1d95" stroke="#000000"/>')
    f.text(x0+66, y, "Phlegraean Fields, the source", 19, color=MUTED, anchor="start")
    y += 34
    f.raw(f'<circle cx="{x0+38}" cy="{y}" r="5" fill="#ffffff" stroke="#5f5e5a" stroke-width="1.2"/>'); f.text(x0+66, y, f"{len(R)-len(arch)-1} other findspots", 19, color=MUTED, anchor="start")
    y += 34
    f.raw(f'<circle cx="{x0+38}" cy="{y}" r="12" fill="#ffffff" stroke="#9a3412" stroke-width="2.5"/>'); f.text(x0+66, y, "Location certainty low or dubious", 19, color=MUTED, anchor="start", maxw=310)
    f.text(x0+22, H-46, "Modern coastline: Natural Earth. Data: geo-lod", 16, color=MUTED, anchor="start", maxw=355)
    f.save()



OWL_B = ("#fbbf24", "#000000", "#000000")
GL, ST = ("#fff2cc", "#000000", "#000000"), ("#d8ead3", "#000000", "#000000")
PILL = {"crm": "#d4e1f5", "sci": "#ffcc99", "arch": "#e3d5f0", "w3c": "#e4e4e0", "plan": "#ffffff"}
AN, W3 = ("#f7dbe8", "#000000", "#000000"), ("#e4e4e0", "#000000", "#000000")


def cbox(f, x, y, w, h, name, anchor=None, fam="crm", st=GL, sub=None):
    """A class in the style of the CRM family diagrams; the pill names its anchor."""
    f.rect(x, y, w, h, st[0], "#000000", 14, 1.2)
    if anchor is None and sub is None:
        f.text(x+w/2, y+h/2, name, 21, True, "#000000", maxw=w-10); return
    tight = bool(anchor and sub) and h < 110
    f.text(x+w/2, y+(20 if tight else h*.30), name, 21, True, "#000000", maxw=w-10)
    if sub is not None:
        for i, t in enumerate(sub if isinstance(sub, list) else [sub]):
            f.text(x+w/2, y+(46 if tight else h*.30+27)+i*24, t, 17 if tight else 18, False, "#000000", maxw=w-10)
    if anchor:
        tw_ = tw(anchor, 16)+18; py_ = y+h-33
        f.rect(x+w/2-tw_/2, py_, tw_, 25, PILL[fam], "#000000", 12, 1.2 if fam == "plan" else .8, fam == "plan")
        f.text(x+w/2, py_+12.5, anchor, 16, False, "#000000")


def label(f, x, y, t, anchor="middle"):
    """A property name on a white ground, as in the CRM family figures."""
    w = tw(t, 16)+10; x0 = x-w/2 if anchor == "middle" else x
    f.rect(x0, y-12, w, 24, "#ffffff", "none"); f.text(x0+w/2, y, t, 16, True, "#000000")


def model_legend(f, y, items, x=40):
    f.text(x, y-34, "Models", 22, True, anchor="start")
    for fill, t in items:
        f.rect(x, y-13, 36, 26, fill, "#000000", 3); f.text(x+46, y, t, 20, anchor="start"); x += 46+tw(t, 20)+36


def fig8():
    f = Fig("08-geo-lod-ontology", "Classes and properties of the geo-lod model")
    A, B, C, D, w, h = 40, 480, 930, 1400, 290, 96
    r = [36, 215, 390, 565, 730]
    c = lambda *a, **k: cbox(f, *a, **k)
    c(A, r[0], w, h, "ObservableProperty", "S9 Property Type", "sci")
    c(C, r[0], w, h, "MarineIsotopeStage", "E4 Period")
    c(D, r[0], w+20, h, "Chronology", "S4 Observation", "sci")
    c(A, r[1], w, h, "DataSource", "E73 Information Object")
    c(B, r[1], w, h, "PalaeoclimateObservation", "S4 Observation", "sci")
    c(C, r[1], w, h, "MISMembershipAssignment", "E13 Attribute Assignment")
    c(D, r[1], w+20, h, "MISAttributeAssignment", "E13 Attribute Assignment")
    c(A, r[2], w, h, "SamplingLocation", "E53 Place")
    c(B, r[2], w, h, "PalaeoclimateSample", "E18 Physical Thing")
    c(C, r[2], w, h, "strat:AgeControlPoint", "E13 Attribute Assignment", st=ST)
    c(D, r[2], w+20, h, "DepthPosition", "E54 Dimension")
    c(A, r[3], 140, h-20, "DrillingSite"); c(A+150, r[3], 140, h-20, "Cave")
    c(A, r[4], w, h, "CIFindspot", "E27 Site")
    c(B, r[3], 142, h, "IceCore", "E22"); c(B+148, r[3], 142, h, "Speleothem")
    c(B, r[4], w, h, "DrillingCampaign", "S1 Matter Removal", "sci")
    c(C, r[3], w, h, "GrowthHiatus", "A3 Stratigraphic Interface", "arch")
    c(C, r[4], w, h, "SpeleothemSample", "E18 Physical Thing")
    c(D, r[3], w+20, h, "AgeModel", "S6 Data Evaluation", "sci")
    c(D, r[4], w+20, h, "AgeAssignment", "E13 Attribute Assignment")
    # subclass arrows
    f.line(A+70, r[3], A+70, r[2]+h+1, "t"); f.line(A+220, r[3], A+220, r[2]+h+1, "t")
    f.line(B+71, r[3], B+71, r[2]+h+1, "t"); f.line(B+219, r[3], B+219, r[2]+h+1, "t")
    # observation
    ob = r[1]
    f.path(f"M {B+40} {ob} L {B+40} 84 L {A+w+2} 84", "a"); label(f, B+40, 150, "sosa:observedProperty")
    f.path(f"M {B+250} {ob} L {B+250} 84 L {C-2} 84", "a"); label(f, (B+250+C)/2, 84, "fallsWithinStage")
    f.path(f"M {B+145} {ob} L {B+145} 14 L {D+155} 14 L {D+155} {r[0]-2}", "a"); label(f, 1000, 14, "ageChronology")
    f.line(B, ob+48, A+w+2, ob+48); label(f, (A+w+B)/2, ob+24, "wasDerivedFrom")
    f.path(f"M {B+40} {ob+h} L {B+40} {ob+h+22} L {(A+w+B)/2} {ob+h+22} L {(A+w+B)/2} {r[2]+26} L {A+w+2} {r[2]+26}", "a"); label(f, (A+w+B)/2, r[2]-14, "P7 took place at")
    f.line(B+145, ob+h, B+145, r[2]-2); label(f, B+172, ob+h+40, "hasFeatureOfInterest", "start")
    f.line(B, r[2]+70, A+w+2, r[2]+70); label(f, (A+w+B)/2, r[2]+70+16, "extractedFrom")
    f.line(C, ob+48, B+w+2, ob+48); label(f, (B+w+C)/2, ob+24, "P140 assigned to")
    f.line(C+145, ob, C+145, r[0]+h+2); label(f, C+145, (ob+r[0]+h)/2, "P141 assigned")
    f.path(f"M {D} {ob+48} L {(C+w+D)/2} {ob+48} L {(C+w+D)/2} 84 L {C+w+2} 84", "a"); label(f, (C+w+D)/2, 140, "P140 assigned to")
    f.line(D+155, ob, D+155, r[0]+h+2); label(f, D+155, (ob+r[0]+h)/2, "inChronology")
    f.line(D+155, ob+h, D+155, r[2]-2); label(f, D+155, (ob+h+r[2])/2, "P141 assigned")
    # drilling and speleothem
    f.line(B+71, r[4], B+71, r[3]+h+2); label(f, B+71, (r[4]+r[3]+h)/2, "O1 removed")
    sp = B+290
    f.path(f"M {C} {r[2]+70} L {sp+40} {r[2]+70} L {sp+40} {r[3]+24} L {sp+2} {r[3]+24}", "a"); label(f, sp+58, r[2]+100, "constrainsSpeleothem", "start") if False else None
    label(f, (sp+C)/2+10, r[2]+70-16, "constrains")
    f.line(C, r[3]+48, sp+2, r[3]+48); label(f, (sp+C)/2+10, r[3]+70, "inSpeleothem")
    f.path(f"M {C} {r[4]+48} L {sp+40} {r[4]+48} L {sp+40} {r[3]+80} L {sp+2} {r[3]+80}", "a"); label(f, (sp+C)/2+22, r[4]+70, "collectedFrom")
    f.path(f"M {C+w} {r[2]+70} L {(C+w+D)/2} {r[2]+70} L {(C+w+D)/2} {r[3]+24} L {D-2} {r[3]+24}", "a"); label(f, (C+w+D)/2, r[2]+70+30, "usedInAgeModel")
    f.line(C+w, r[3]+70, D-2, r[3]+70); label(f, (C+w+D)/2, r[3]+90, "respectedByAgeModel")
    f.line(D+155, r[4], D+155, r[3]+h+2); label(f, D+155, (r[4]+r[3]+h)/2, "ageModel")
    f.line(C+w, r[4]+48, D-2, r[4]+48); label(f, (C+w+D)/2, r[4]+24, "hasAgeAssignment")
    model_legend(f, 918, [(GL[0], "geo-lod"), (ST[0], "strat:"), (PILL["crm"], "CIDOC CRM"), (PILL["sci"], "CRMsci"), (PILL["arch"], "CRMarchaeo")])
    f.line(1010, 918, 1058, 918, "t"); f.text(1068, 918, "subclass of", 20, anchor="start")
    f.line(1230, 918, 1278, 918, "a"); f.text(1288, 918, "property, as used in the graph", 20, anchor="start")
    f.text(40, 970, "Selected classes of 46 in geo_lod_core, EPICA and SISAL. A pill names the CRM-family anchor; a class without one inherits it.", 18, color=MUTED, anchor="start", maxw=1670)
    f.save()


def fig9():
    f = Fig("09-geo-lod-instance", "A semantic representation of one CH4 measurement from the EPICA Dome C core")
    w, h = 340, 110
    GREY = ("#e4e4e0", "#000000", "#000000")
    c = lambda x, y, n, s, st=GL, ww=w: cbox(f, x, y, ww, h, n, sub=s, st=st)
    X1, X2, X3, W3 = 40, 560, 1090, 420
    c(X1, 40, "DataSource", ["Spahni & Stocker 2006"])
    c(X2, 40, "ObservableProperty", ["Methane (CH₄), ppbv"])
    c(X3, 40, "MarineIsotopeStage", ["MIS 5, warm stage"], ww=W3)
    c(X3, 215, "MISMembershipAssignment", ["observation falls in MIS 5"], ww=W3)
    c(X1, 395, "IceCore", ["EPICA Dome C core"])
    c(X2, 395, "IceCoreObservation", ["Methane, 436.3 ppbv", "at 1782.015 m"])
    c(X3, 395, "IceCoreChronology", ["EDC2-gas"], ww=W3)
    c(X3, 575, "MISAttributeAssignment", ["Beginning of MIS 5", "at 1782.26 m"], ww=W3)
    c(X1, 750, "DrillingSite", ["EPICA Dome C,", "East Antarctica"])
    c(X2, 750, "time:TimePosition", ["132.16 ka", "on EDC2-gas"], GREY)
    c(X3, 750, "DepthPosition", ["1782.26 m"], ww=W3)
    f.line(X2+170, 395, X2+170, 152); label(f, X2+170, 275, "sosa:observedProperty")
    f.path(f"M {X2+50} 395 L {X2+50} 210 L {X1+170} 210 L {X1+170} 152", "a"); label(f, 400, 210, "prov:wasDerivedFrom")
    f.line(X2, 450, X1+342, 450); label(f, (X1+340+X2)/2, 426, "hasFeatureOfInterest")
    f.line(X1+120, 505, X1+120, 748); label(f, X1+120, 625, "extractedFrom")
    f.path(f"M {X2+50} 505 L {X2+50} 640 L {X1+290} 640 L {X1+290} 748", "a"); label(f, 470, 640, "P7 took place at")
    f.line(X2+230, 505, X2+230, 748); label(f, X2+230, 625, "hasTimePosition")
    f.path(f"M {X3} 270 L {X2+290} 270 L {X2+290} 393", "a"); label(f, 995, 246, "P140 assigned to")
    f.line(X3+210, 215, X3+210, 152); label(f, X3+210, 184, "P141 assigned")
    f.line(X2+340, 450, X3-2, 450); label(f, (X2+340+X3)/2, 426, "ageChronology")
    f.line(X3+210, 575, X3+210, 507); label(f, X3+210, 541, "inChronology")
    f.line(X3+210, 685, X3+210, 748); label(f, X3+210, 716, "P141 assigned")
    f.path(f"M {X3+W3} 630 L 1600 630 L 1600 95 L {X3+W3+2} 95", "a"); label(f, 1600, 360, "P140 assigned to")
    model_legend(f, 925, [(GL[0], "geo-lod"), ("#e4e4e0", "OWL-Time")])
    f.text(560, 925, "Each class shown is the most specific one; figure 08 gives its CRM-family anchor.", 20, color=MUTED, anchor="start", maxw=1150)
    f.save()

def fig10():
    f = Fig("10-strat-ontology", "Classes and properties of the strat module")
    A, B, C, D, w, h = 40, 500, 960, 1400, 290, 96
    aw = 255
    r = [36, 215, 390, 565, 730]
    c = lambda *a, **k: cbox(f, *a, **k)
    c(A, r[0], aw, h, "time:TRS", "E29 Design or Procedure", st=W3)
    c(B, r[0], w, h, "Core", "E18 Physical Thing", "plan", st=ST)
    c(C, r[0], w, h, "AgeDepthModel", st=ST)
    c(D, r[0], w+20, h, "AgeControlPoint", "E13 Attribute Assignment", st=ST)
    c(A, r[1], aw, h, "skos:Concept", "E55 Type", sub="lithology, colour, structure", st=W3)
    c(B, r[1], w, h, "StratigraphicUnit", "A2 Volume Unit", "plan", st=ST)
    c(C, r[1], w, h, "TephraClass", "E55 Type", sub="primary, secondary", st=ST)
    c(D, r[1], w+20, h, "geolod:Speleothem", "E18 Physical Thing")
    c(B, r[2], w, h, "LithologicalUnit", st=ST)
    c(C, r[2], w, h, "Boundary", "A3 Stratigraphic Interface", "plan", st=ST)
    c(B, r[3], w, h, "TephraLayer", st=ST)
    c(C, r[3], w, h, "skos:Concept", "E55 Type", sub="marker: HBT, GLT, JWT", st=W3)
    c(A, r[4], aw, h, "Locality", "E1 via geo:Feature", st=ST)
    c(B, r[4], w, h, "an:Specimen", "E18 via sosa:Sample", st=AN)
    c(C, r[4], w, h, "Eruption", "E5 Event", "plan", st=ST)
    f.line(B, r[0]+48, A+aw+2, r[0]+48); label(f, (A+aw+B)/2, r[0]+24, "depthReferenceSystem")
    f.line(B+w, r[0]+48, C-2, r[0]+48); label(f, (B+w+C)/2, r[0]+24, "hasAgeModel")
    f.line(C+w, r[0]+48, D-2, r[0]+48); label(f, (C+w+D)/2, r[0]+24, "hasControlPoint")
    f.line(B+145, r[1], B+145, r[0]+h+2); label(f, B+145, (r[1]+r[0]+h)/2, "partOfCore")
    f.line(D+155, r[0]+h, D+155, r[1]-2); label(f, D+155, (r[1]+r[0]+h)/2, "constrainsSpeleothem")
    f.line(B, r[1]+48, A+aw+2, r[1]+48); label(f, (A+aw+B)/2, r[1]+24, "hasLithology ...")
    f.line(B+w, r[1]+30, C-2, r[1]+30); label(f, (B+w+C)/2, r[1]+8, "tephraClass")
    f.path(f"M {B+w} {r[1]+62} L {B+w+40} {r[1]+62} L {B+w+40} {r[1]+86} L {B+w+2} {r[1]+86}", "a"); label(f, B+w+110, r[1]+122, "overlies, meets, Allen")
    f.line(B+145, r[2], B+145, r[1]+h+1, "t"); f.line(B+145, r[3], B+145, r[2]+h+1, "t")
    f.line(B+w, r[3]+30, C-2, r[3]+30); label(f, (B+w+C)/2, r[3]+8, "markerTephra")
    f.path(f"M {B+w} {r[3]+70} L {(B+w+C)/2} {r[3]+70} L {(B+w+C)/2} {r[4]+48} L {C-2} {r[4]+48}", "a"); label(f, (B+w+C)/2, r[3]+h+30, "producedByEruption")
    f.path(f"M {B} {r[1]+74} L 462 {r[1]+74} L 462 {r[4]+30} L {B-2} {r[4]+30}", "a"); label(f, 440, r[2]+h+40, "hostsSpecimen")
    f.line(B, r[4]+72, A+aw+2, r[4]+72); label(f, (A+aw+B)/2, r[4]+92, "sampledAt")
    f.path(f"M {A+127} {r[4]} L {A+127} {r[4]-40} L 462 {r[4]-40}", None)
    model_legend(f, 918, [(ST[0], "strat:"), (GL[0], "geolod:"), (AN[0], "an:"), (W3[0], "W3C")])
    f.rect(790, 906, 62, 24, "#ffffff", "#000000", 12, 1.2, True); f.text(862, 918, "CRM counterpart documented, not yet in crm_bridging.ttl", 20, anchor="start")
    f.rect(790, 950, 62, 24, PILL["crm"], "#000000", 12, .8); f.text(862, 962, "Anchored in the graph today", 20, anchor="start")
    f.line(1200, 962, 1248, 962, "t"); f.text(1258, 962, "subclass of", 20, anchor="start")
    f.save()


def fig11():
    f = Fig("11-analysis-ontology", "Classes and properties of the analysis module")
    w, h = 340, 130
    A, B, C = 40, 700, 1370
    c = lambda x, y, n, a=None, fam="crm", st=AN, sub=None, ww=w: cbox(f, x, y, ww, h, n, a, fam, st, sub)
    c(A, 60, "strat:StratigraphicUnit", "A2 Volume Unit", "plan", ST)
    c(A, 345, "Specimen", "E18 via sosa:Sample", sub="an:sampleDepth")
    c(B, 345, "Analysis", "S4 via sosa:Observation", "sci", sub="one value on one specimen")
    c(C, 345, "Property", "S9 via sosa:ObservableProperty", "sci", sub="oxide wt%, element ppm", ww=340)
    c(B, 60, "Method", "E55 via skos:Concept", sub="EPMA, LA-ICP-MS")
    c(C, 60, "ChEBI", None, st=W3, sub="the chemical entity")
    c(B, 640, "DerivedValue", sub="fraction from counts, TMAF")
    c(A, 640, "QualityFlag", "E55 via skos:Concept", sub="below detection limit")
    c(C, 640, "qudt:QuantityValue", None, st=W3, sub="value and unit")
    f.line(A+170, 190, A+170, 343); label(f, A+170, 268, "strat:hostsSpecimen")
    f.line(B, 410, A+342, 410); label(f, (A+340+B)/2, 386, "sosa:hasFeatureOfInterest")
    f.line(B+340, 410, C-2, 410); label(f, (B+340+C)/2, 386, "sosa:observedProperty")
    f.line(B+170, 345, B+170, 192); label(f, B+170, 268, "sosa:usedProcedure")
    f.line(C+170, 345, C+170, 192); label(f, C+170, 268, "an:analyte")
    f.line(B+170, 640, B+170, 476, "t")
    f.path(f"M {B+280} 640 L {B+280} 580 L {B+500} 580 L {B+500} 450 L {B+342} 450", None) if False else None
    f.path(f"M {B+60} 475 L {B+60} 560 L {A+290} 560 L {A+290} 638", "a"); label(f, 480, 560, "an:qualityFlag")
    f.path(f"M {B+280} 475 L {B+280} 560 L {C+170} 560 L {C+170} 638", "a"); label(f, 1200, 560, "sosa:hasResult")
    f.text(B+170, 806, "prov:wasDerivedFrom names the inputs", 18, color=MUTED)
    model_legend(f, 918, [(AN[0], "an:"), (ST[0], "strat:"), (W3[0], "external")])
    f.rect(610, 906, 62, 24, PILL["crm"], "#000000", 12, .8); f.text(682, 918, "Reached through crm_bridging.ttl", 20, anchor="start")
    f.rect(1050, 906, 62, 24, "#ffffff", "#000000", 12, 1.2, True); f.text(1122, 918, "Documented, not yet bridged", 20, anchor="start")
    f.line(1430, 918, 1478, 918, "t"); f.text(1488, 918, "subclass of", 20, anchor="start")
    f.text(40, 970, "The module itself names no CRM class; the sosa: and skos: parents carry the anchors. The sosa: properties are reused as documented in the file.", 18, color=MUTED, anchor="start", maxw=1670)
    f.save()


def fig12():
    f = Fig("12-modules-and-crm", "How the geolod, strat and an modules connect to the CIDOC CRM family")
    f.rect(30, 24, 1690, 262, "#eef2f9", "#000000", 14, 1)
    f.text(60, 58, "CRM family", 26, True, anchor="start")
    f.box(60, 84, 1630, 70, "CIDOC CRM", "E13, E18, E53, E55, E4, E54 ...", ("#d4e1f5", "#000000", "#000000"), 23, 18, rx=10)
    for x, a, b, col in ((60, "CRMsci", "S4, S6, S9, S1", "#ffcc99"), (610, "CRMarchaeo", "A3, A2", "#e3d5f0"), (1160, "CRMgeo", "SP6", "#d9ead3")):
        f.box(x, 174, 530, 90, a, b, (col, "#000000", "#000000"), 23, 18, rx=10)
    X = [(40, 470), (650, 480), (1270, 440)]
    f.box(650, 340, 1060, 70, "crm_bridging.ttl", "anchors SOSA, PROV, GeoSPARQL, SKOS, OWL-Time, DCAT and one strat: class", OWL_B, 22, 18, rx=10)
    mods = [("geolod:", ["geo_lod_core, epica_ontology, sisal_ontology", "46 classes with subclass axioms into CRM", "archive, chronology, stage, hiatus"], GL),
            ("strat:", ["strat.ttl, 10 classes", "CRM-free by design", "core, unit, tephra, boundary, age model"], ST),
            ("an:", ["analysis_core.ttl, 6 classes", "CRM-free by design", "specimen, analysis, method, property"], AN)]
    for (x, ww), (n, lines, st) in zip(X, mods):
        f.rect(x, 470, ww, 170, st[0], "#000000", 14, 1.2)
        f.text(x+ww/2, 504, n, 27, True, "#000000")
        for i, t in enumerate(lines):
            f.text(x+ww/2, 542+i*30, t, 19, color="#000000", maxw=ww-16)
    f.line(275, 470, 275, 288); label(f, 275, 380, "direct rdfs:subClassOf")
    f.line(1180, 340, 1180, 288)
    f.line(890, 470, 890, 412); label(f, 890, 442, "1 class now, more planned")
    f.line(1490, 470, 1490, 412); label(f, 1490, 442, "through SOSA, SKOS")
    f.line(650, 570, 512, 570); label(f, 580, 546, "AgeControlPoint")
    f.line(1130, 570, 1268, 570); label(f, 1200, 546, "hostsSpecimen")
    f.box(650, 700, 1060, 76, "W3C and community standards", "SOSA/SSN, OWL-Time, GeoSPARQL, PROV-O, SKOS, DCAT, QUDT", W3, 22, 18, rx=10)
    f.line(890, 640, 890, 698); f.line(1490, 640, 1490, 698)
    f.path("M 275 640 L 275 738 L 648 738", "a"); label(f, 460, 738, "reused with subclasses")
    f.text(40, 815, "Where each figure stands", 22, True, anchor="start")
    for (x, ww), (a, b, st) in zip(X, (("Ice core, stalagmite, CI findspots", "geolod:, one strat: class; 01 to 05, 08, 09", GL),
                                        ("WD1 and tephra", "strat:, an:; 06, 07, data still planned", ST),
                                        ("Vocabularies", "mis:, trs:, tephra: reserved", W3))):
        f.box(x, 840, ww, 86, a, b, st, 22, 18, rx=10)
    f.save()


ITEMS = [
 ("01-from-measurement-to-crm", "From one table row to CIDOC CRM and its extensions.", "Data: EPICA Dome C, Spahni & Stocker 2006, doi:10.1594/PANGAEA.472484; figure CC BY 4.0."),
 ("02-crm-family", "Extensions specialise CIDOC CRM classes rather than replace them.", "Classes: geo-lod, CIDOC CRM, CRMsci 2.0, CRMarchaeo 1.4.8; figure CC BY 4.0."),
 ("03-stratigraphy-time", "One stage boundary, five chronologies, 48 m apart in the same core.", "Data: EPICA Dome C via geo-lod; stage boundary after Railsback et al. 2015; figure CC BY 4.0."),
 ("04-measured-dated-interpreted", "Measured, dated and interpreted statements about one stalagmite.", "Data: SISAL v3, LSF13_2018; outline schematic; figure CC BY 4.0."),
 ("05-ci-map", "Archaeological sites with Campanian Ignimbrite tephra, up to 2,234 km from the source.", "Data: geo-lod CI findspots; coastline Natural Earth; figure CC BY 4.0."),
 ("06-ci-model", "The graph records where; the measurement shows what.", "Data: Schenk et al. 2024, Quaternary 7, 17; dashed nodes are planned; figure CC BY 4.0."),
 ("07-walsdorf-wd1", "Core WD1: depth is measured, age is modelled.", "Data: Schenk et al. 2026, Quaternary 9, 67; tables CC BY 4.0, Fiona Schenk; dashed nodes are illustrative."),
 ("08-geo-lod-ontology", "Classes and properties of the geo-lod model.", "Selected classes; each anchored in the CIDOC CRM family; figure CC BY 4.0."),
 ("09-geo-lod-instance", "One methane measurement as a semantic representation.", "Data: EPICA Dome C, Spahni & Stocker 2006, doi:10.1594/PANGAEA.472484; figure CC BY 4.0."),
 ("10-strat-ontology", "The strat module: stratigraphy of a core.", "Ontology: strat.ttl; dashed anchors are planned; figure CC BY 4.0."),
 ("11-analysis-ontology", "The an module: one analysis of one specimen.", "Ontology: analysis_core.ttl; anchors through crm_bridging.ttl; figure CC BY 4.0."),
 ("12-modules-and-crm", "Three modules, one CRM family.", "Ontology modules of geo-lod; figure CC BY 4.0."),
]

def caption_page():
    import site_kit
    cards = [site_kit.fig_card(IMG, n, str(i), c, cr) for i, (n, c, cr) in enumerate(ITEMS, 1)]
    intro = ("Twelve figures for the semantic-modelling section of the CHNT31 talk. The classes and properties behind them, "
             'the CRM coverage and a query page are in the <a href="../docu/index.html">documentation</a>.')
    site_kit.write_assets(SITE)
    site_kit.write_page(SITE/"index.html", site_kit.page("visuals", "index.html", "Slide figures", intro, "\n".join(cards)))


def slides():
    check_quoted_values()
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7(); fig8(); fig9(); fig10(); fig11(); fig12()
    caption_page()
    print(f"Wrote {len(list(IMG.glob('*.png')))} figures and index.html to {SITE}")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Slide figures (visuals/site/) and the documentation pages (docu/).")
    ap.add_argument("--only", choices=["slides", "docu"], help="build one of the two; default is both")
    args = ap.parse_args(argv)
    if args.only != "docu":
        slides()
    if args.only != "slides":
        import docu
        docu.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
