"""paper_figs.py - the figures of the ECEASST paper, drawn for the column of the paper.

The paper text is 420 pt wide. A figure that is 1750 px wide, as the slide figures are, arrives there at 0.24 pt per
pixel, and its 15 to 24 px type becomes 3.6 to 5.8 pt. These figures are 1700 px wide with type of 22 px and more
(5.4 pt and more at 420 pt), fewer nodes, and edge labels as short CRM property numbers that the caption spells out.

Everything that is drawn is read from the committed graphs; nothing here is typed by hand that the graph states.

    py visuals/paper_figs.py            # all
    py visuals/paper_figs.py eruption   # one

Output: docu/img/paper/<name>.svg and .png (PNG for LaTeX: the SVGs name Fira Sans without embedding it).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from rdflib import Namespace  # noqa: E402
from rdflib.namespace import RDF, SKOS  # noqa: E402

import cluster_archaeology as AY  # noqa: E402
from build import AN, CLS, GL, INST, MUTED, OWL, ST, TERM, W3, Fig, chip, tw  # noqa: E402

REPO = HERE.parent
OUT = REPO / "docu" / "img" / "paper"
W = 1700
CRM, G = AY.CRM, AY.G
MIN_TYPE = 22      # px; 5.4 pt at 420 pt


def _t(f: Fig, x, y, text, size=MIN_TYPE, med=False, color=None, anchor="middle", maxw=None):
    if size < MIN_TYPE:
        raise ValueError(f"{f.name}: type of {size} px is too small for the column of the paper (minimum {MIN_TYPE})")
    f.text(x, y, text, size, med, color or "#1f1f1d", anchor, maxw)


def volcano(f: Fig, x, y, w, h):
    """Stylised volcano: shaded cone, glowing crater, lava runs, an ash plume and a few sparks (decoration, no data)."""
    cx, top, base = x + w / 2, y + h * 0.50, y + h
    hw = 26                                  # half width of the crater rim
    for (dx, dy, rr, c) in ((-4, -10, 24, "#8b919b"), (22, -34, 22, "#a3a8b1"), (-18, -52, 19, "#b8bcc4"),
                            (14, -76, 16, "#cdd0d6"), (40, -92, 13, "#dde0e4"), (-4, -96, 11, "#e8eaed")):
        f.raw(f'<circle cx="{cx + dx:.1f}" cy="{top + dy:.1f}" r="{rr}" fill="{c}" stroke="#6b7280" stroke-width="1.2"/>')
    left = f'M{x},{base} Q{cx - hw - 22:.1f},{top + 50:.1f} {cx - hw:.1f},{top:.1f}'
    right = f'L{cx + hw:.1f},{top:.1f} Q{cx + hw + 22:.1f},{top + 50:.1f} {x + w},{base} Z'
    f.raw(f'<path d="{left} {right}" fill="#7c4a26" stroke="#000000" stroke-width="2.5" stroke-linejoin="round"/>')
    f.raw(f'<path d="M{cx:.1f},{top:.1f} L{cx + hw:.1f},{top:.1f} Q{cx + hw + 22:.1f},{top + 50:.1f} {x + w},{base} L{cx + 14:.1f},{base} Z" fill="#5a3418" opacity=".55"/>')
    f.raw(f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{hw}" ry="9" fill="#f97316" stroke="#000000" stroke-width="2"/>')
    f.raw(f'<ellipse cx="{cx:.1f}" cy="{top + 1:.1f}" rx="{hw - 9}" ry="4.5" fill="#fde047"/>')
    for (x0, dx1, dy1) in ((-12, -16, 52), (4, 6, 62), (14, 30, 48)):
        f.raw(f'<path d="M{cx + x0:.1f},{top + 6:.1f} q{dx1 / 2:.1f},{dy1 / 2:.1f} {dx1:.1f},{dy1}" fill="none" stroke="#dc2626" stroke-width="5" stroke-linecap="round"/>')
    for (dx, dy) in ((-44, -18), (52, -22), (-58, -44), (66, -52)):
        f.raw(f'<circle cx="{cx + dx:.1f}" cy="{top + dy:.1f}" r="4" fill="#f97316" stroke="#000000" stroke-width=".8"/>')


ZOOM = (13.55, 40.45, 15.05, 41.15)     # lon0, lat0, lon1, lat1 of the Bay of Naples zoom


def _haversine(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(d))


def naples(f: Fig, D: AY.ArchData, x, y, w):
    """Zoom on the Bay of Naples from the Natural Earth land file of the repository. The source area is marked (schematic),
    and one arrow per compass sector points towards the findspots of that sector: its direction is the bearing of the
    farthest findspot in the sector. Returns the height of the map and the largest distance to a findspot in km."""
    import geo_lod_basemap as BM
    bbox = ZOOM
    k = math.cos(math.radians((bbox[1] + bbox[3]) / 2))
    h = round(w * (bbox[3] - bbox[1]) / ((bbox[2] - bbox[0]) * k))
    X = lambda lon: round(x + (lon - bbox[0]) / (bbox[2] - bbox[0]) * w, 1)
    Y = lambda lat: round(y + (bbox[3] - lat) / (bbox[3] - bbox[1]) * h, 1)
    f.rect(x, y, w, h, "#eef3f7", "#bdbbb2", 6, 1)
    tol = (bbox[2] - bbox[0]) / w * 0.4
    land = []
    for ring in BM._rings_of(BM.land_path(str(D.repo))):
        xs, ys = [q[0] for q in ring], [q[1] for q in ring]
        if max(xs) < bbox[0] or min(xs) > bbox[2] or max(ys) < bbox[1] or min(ys) > bbox[3]:
            continue
        cut = BM.simplify(BM.clip_ring(ring, bbox), tol)
        if len(cut) >= 3:
            land.append("M" + " L".join(f"{X(a)} {Y(b)}" for a, b in cut) + "Z")
    f.raw(f'<path d="{" ".join(land)}" fill="#f4f1e6" stroke="#9c998a" stroke-width="1.4" stroke-linejoin="round"/>')
    slon, slat = 14.14, 40.83        # Phlegraean Fields (Wikidata Q755123); the marker is schematic
    mx, my = X(slon), Y(slat)
    # one arrow per 45 degree sector that holds findspots, towards the farthest of them
    sectors = {}
    for (_, lon, lat, *_r) in D.findspots:
        dist = _haversine(slon, slat, lon, lat)
        if dist < 25:
            continue
        brg = math.degrees(math.atan2((lon - slon) * math.cos(math.radians(slat)), lat - slat)) % 360
        sec = int(((brg + 22.5) % 360) // 45)
        if sec not in sectors or dist > sectors[sec][0]:
            sectors[sec] = (dist, brg)
    for dist, brg in sectors.values():
        dx, dy = math.sin(math.radians(brg)), -math.cos(math.radians(brg))
        lim = min((x + w - 22 - mx) / dx if dx > 1e-6 else 1e9, (x + 22 - mx) / dx if dx < -1e-6 else 1e9,
                  (y + h - 22 - my) / dy if dy > 1e-6 else 1e9, (y + 22 - my) / dy if dy < -1e-6 else 1e9)
        ln = min(108, lim)
        x1, y1, x2, y2 = mx + dx * 22, my + dy * 22, mx + dx * ln, my + dy * ln
        f.raw(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#dc2626" stroke-width="5" stroke-linecap="round"/>')
        hx, hy = -dy, dx
        f.raw(f'<polygon points="{x2 + dx * 16:.1f},{y2 + dy * 16:.1f} {x2 + hx * 9:.1f},{y2 + hy * 9:.1f} {x2 - hx * 9:.1f},{y2 - hy * 9:.1f}" fill="#dc2626"/>')
    f.raw(f'<circle cx="{mx}" cy="{my}" r="13" fill="#ffffff" stroke="#dc2626" stroke-width="3"/>')
    f.raw(f'<circle cx="{mx}" cy="{my}" r="6" fill="#dc2626" stroke="#000000" stroke-width="1"/>')
    far = max(_haversine(slon, slat, lon, lat) for (_, lon, lat, *_r) in D.findspots)
    return h, far


def boot(f: Fig, D: AY.ArchData, x, y, w, frame, zoom_box):
    """Italy as a small overview with the frame of the zoom map in red; thin lines join the frame to the zoom map."""
    import geo_lod_basemap as BM
    bbox = (6.3, 36.2, 19.0, 47.2)
    k = math.cos(math.radians((bbox[1] + bbox[3]) / 2))
    h = round(w * (bbox[3] - bbox[1]) / ((bbox[2] - bbox[0]) * k))
    X = lambda lon: round(x + (lon - bbox[0]) / (bbox[2] - bbox[0]) * w, 1)
    Y = lambda lat: round(y + (bbox[3] - lat) / (bbox[3] - bbox[1]) * h, 1)
    f.rect(x, y, w, h, "#eef3f7", "#bdbbb2", 6, 1)
    tol = (bbox[2] - bbox[0]) / w * 0.5
    land = []
    for ring in BM._rings_of(BM.land_path(str(D.repo))):
        xs, ys = [q[0] for q in ring], [q[1] for q in ring]
        if max(xs) < bbox[0] or min(xs) > bbox[2] or max(ys) < bbox[1] or min(ys) > bbox[3]:
            continue
        cut = BM.simplify(BM.clip_ring(ring, bbox), tol)
        if len(cut) >= 3:
            land.append("M" + " L".join(f"{X(a)} {Y(b)}" for a, b in cut) + "Z")
    f.raw(f'<path d="{" ".join(land)}" fill="#f4f1e6" stroke="#9c998a" stroke-width="1.4" stroke-linejoin="round"/>')
    x0, y0, x1, y1 = X(frame[0]), Y(frame[3]), X(frame[2]), Y(frame[1])
    zx, zy, zw, zh = zoom_box
    for (ax, ay, bx_, by_) in ((x0, y0, zx, zy + zh + 2), (x1, y0, zx + zw, zy + zh + 2)):
        f.raw(f'<line x1="{ax}" y1="{ay}" x2="{bx_}" y2="{by_}" stroke="#dc2626" stroke-width="1.6" stroke-dasharray="6 5"/>')
    f.raw(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="#ffffff" fill-opacity=".35" stroke="#dc2626" stroke-width="3"/>')
    return h


def _panel_title(f, y, letter, text):
    f.rect(20, y - 24, 40, 40, "#000000", "#000000", 6, 1)
    _t(f, 40, y - 3, letter, 28, True, color="#ffffff")
    _t(f, 76, y - 3, text, 28, True, anchor="start")


def _ci_uncertainty(f, rows):
    """Panel b: from the published statement to the age with its uncertainty node and interval, as in the graph."""
    A, B, C, D_ = (20, 290), (470, 360), (1060, 250), (1495, 185)
    for (x, w), t in zip((A, B, C, D_), ("As published", "Time position", "Uncertainty node", "Interval")):
        _t(f, x + w / 2, 0, t, 26, True, color=MUTED)
    for i, r in enumerate(rows):
        y = 30 + i * 190
        mid = y + 75
        who = r["who"].replace(" et al.", "")
        pub, _, note = r["published"].partition(" (")
        f.rect(A[0], y, A[1], 150, "#ffffff", "#000000", 6, 1.6)
        cx = A[0] + A[1] / 2
        parts = [t for t in note.rstrip(")").split(", ") if t] or [""]
        _t(f, cx, y + 32, who, 26, True)
        _t(f, cx, y + 66, pub, 22)
        for k, t in enumerate(parts[:2]):
            _t(f, cx, y + 98 + 30 * k, t, 22, color=MUTED)
        f.rect(B[0], y, B[1], 150, W3[0], "#000000", 6, 1.6)
        _t(f, B[0] + 18, y + 32, "time:TimePosition", 24, True, anchor="start")
        _t(f, B[0] + 18, y + 66, f"numericPosition {r['ka']:g}", 22, anchor="start")
        _t(f, B[0] + 18, y + 96, f"ageUncertaintyPos/Neg {r['unc']:g}", 22, anchor="start")
        _t(f, B[0] + 18, y + 126, f"hasTRS trs:{r['trs']}", 22, color=MUTED, anchor="start")
        f.rect(C[0], y, C[1], 150, "#ffffff", "#000000", 6, 1.6)
        cx = C[0] + C[1] / 2
        _t(f, cx, y + 32, "AgeUncertainty", 24, True)
        _t(f, cx, y + 66, f"plusKa {r['unc']:g}", 22)
        _t(f, cx, y + 96, f"minusKa {r['unc']:g}", 22)
        _t(f, cx, y + 126, f"coverageLevel {r['cov']:g}" if r["cov"] else "coverage not stated", 22,
           color=None if r["cov"] else MUTED)
        f.rect(D_[0], y, D_[1], 150, "#ffffff", "#000000", 6, 1.6)
        cx = D_[0] + D_[1] / 2
        _t(f, cx, y + 32, "ProperInterval", 22, True)
        _t(f, cx, y + 72, f"begin {r['older']:.2f}", 22)
        _t(f, cx, y + 102, f"end {r['younger']:.2f}", 22)
        _t(f, cx, y + 132, "ka BP", 22, color=MUTED)
        for x0, x1, lab in ((A[0] + A[1], B[0], "modelled as"), (B[0] + B[1], C[0], "hasAgeUncertainty"),
                            (C[0] + C[1], D_[0], "hasAgeInterval")):
            f.line(x0, mid, x1 - 2, mid, "a")
            chip(f, (x0 + x1) / 2, mid, lab, 22)
    _t(f, 850, 30 + 3 * 190 - 6, "Schenk 2024: (39,940 \u2212 50) / 1000 = 39.890 ka BP (b2k to ka BP). Begin and end keep the TRS of their age.",
       22, color=MUTED)


def eruption(D: AY.ArchData) -> dict:
    """The CI eruption as the root: place, findspots and time-span; one assertion and one bar per published age."""
    ci = D.ci
    ev = G["ci_volcanic_event"]
    place = ci.value(ev, CRM.P7_took_place_at)
    qid = str(ci.value(place, SKOS.closeMatch)).rsplit("/", 1)[-1]
    sites = set(ci.objects(ev, CRM.P12_occurred_in_the_presence_of))
    arch = {x for x in sites if (x, RDF.type, G.CIArchaeologicalSite) in ci}
    rows = AY.eruption_ages(D)
    lo, hi = min(r["ka"] - r["unc"] for r in rows), max(r["ka"] + r["unc"] for r in rows)
    a0, a1 = math.floor((lo - 0.1) * 5) / 5, math.ceil((hi + 0.1) * 5) / 5
    top, step, ph = 440, 175, 140
    H = top + step * (len(rows) - 1) + 150
    HB = 30 + 3 * 190 + 40
    f = Fig("paper-ci-eruption", "The Campanian Ignimbrite eruption with its place, findspots and published ages, and how the ages and their uncertainty are modelled", W, 70 + H + 90 + HB, OUT)
    cy = top + step * (len(rows) - 1) / 2
    _panel_title(f, 36, "a", "The eruption, its place, its findspots and its published ages")
    f.raw('<g transform="translate(0,70)">')
    rx, rw = 360, 210                              # root column
    volcano(f, 50, 10, 250, 230)
    mh, far = naples(f, D, 10, 262, 320)
    bh = boot(f, D, 65, 262 + mh + 50, 210, ZOOM, (10, 262, 320, mh))
    _t(f, 170, 262 + mh + 50 + bh + 30, f"findspots up to {round(far, -1):,.0f} km away", 22, color=MUTED, maxw=320)
    # root and its branches
    bx, bw = 1210, 480
    f.box(rx, 70, rw, 120, "CI eruption", "E5 Event", INST, 28, 24)
    f.box(bx, 20, bw, 96, "Phlegraean Fields", f"E53 Place, wd:{qid}", INST, 26, 24)
    f.box(bx, 144, bw, 96, "Findspots (selection)", f"{len(sites)} E27 Sites, {len(arch)} also A2", INST, 26, 24)
    f.box(rx, cy - 60, rw, 120, "Time-span", "E52 Time-Span", INST, 28, 24)
    for (y2, txt) in ((68, "P7 took place at"), (192, "P12 occurred in the presence of")):
        f.line(rx + rw, 130, bx - 2, y2, "a")
        chip(f, (rx + rw + bx) / 2, (130 + y2) / 2, txt, 24)
    xm = rx + rw / 2
    f.line(xm, 190, xm, cy - 62, "a")
    chip(f, xm, (190 + cy - 60) / 2, "P4 has time-span", 24)
    # one assertion per published age, and its time position as a bar
    ex, ew, px, pw = 930, 200, 1350, 340
    in0, in1 = px + 26, px + pw - 26
    x_of = lambda v: in0 + (v - a0) / (a1 - a0) * (in1 - in0)
    for k in range(round(a0 * 5), round(a1 * 5) + 1):
        if k % 2 == 0:
            _t(f, x_of(k / 5), top - ph / 2 - 22, f"{k / 5:.1f}", 24, color=MUTED)
    _t(f, px + pw, top - ph / 2 - 54, "ka BP", 24, med=True, color=MUTED, anchor="end")
    for i, r in enumerate(rows):
        y = top + i * step
        colour = AY.AGE_ADOPTED if r["adopted"] else AY.AGE_LAYER if r["layer"] else AY.AGE_COMPETING
        f.box(ex, y - 48, ew, 96, r["who"].replace(" et al.", ""), "E13 Assignment", CLS, 26, 24)
        f.line(ex, y, rx + rw + 2, cy, "a")
        chip(f, (ex + rx + rw) / 2, (y + cy) / 2, "P140 assigned attribute to", 24)
        f.line(ex + ew, y, px - 2, y, "a")
        chip(f, (ex + ew + px) / 2, y, "P141 assigned", 24)
        f.rect(px, y - ph / 2, pw, ph, "#ffffff", "#000000", 6, 1)
        _t(f, px + 16, y - ph / 2 + 28, f"{r['ka']:.2f} \u00b1 {r['unc']:.2f} ka", 24, True, anchor="start")
        tt = a0
        while tt <= a1 + 1e-9:
            f.line(x_of(tt), y - 4, x_of(tt), y + 22, None, w=1, color=AY.GRID)
            tt += 0.2
        by = y + 8
        f.line(x_of(r["ka"] - r["unc"]), by, x_of(r["ka"] + r["unc"]), by, None, w=7, color=colour)
        for v in (r["ka"] - r["unc"], r["ka"] + r["unc"]):
            f.line(x_of(v), by - 13, x_of(v), by + 13, None, w=3, color=colour)
        f.raw(f'<circle cx="{x_of(r["ka"]):.1f}" cy="{by}" r="10" fill="{colour}" stroke="#000000" stroke-width="1.5"/>')
        _t(f, px + 16, y + ph / 2 - 22, f"trs:{r['trs']}", 24, color=MUTED, anchor="start", maxw=pw - 32)
    lx_ = 20                                                     # legend at the minimum type of the paper
    for st_, txt_ in (((AY.AGE_ADOPTED,), "adopted age"), ((AY.AGE_COMPETING,), "competing age"), ((AY.AGE_LAYER,), "age of the tephra layer")):
        f.rect(lx_, H - 28 - 11, 22, 22, st_[0], "#000000", 3)
        _t(f, lx_ + 32, H - 28, txt_, MIN_TYPE, color=MUTED, anchor="start")
        lx_ += 32 + tw(txt_, MIN_TYPE) + 36
    f.raw('</g>')
    _panel_title(f, 70 + H + 50, "b", "How an age and its uncertainty (\u00b1 ka) are modelled")
    f.raw(f'<g transform="translate(0,{70 + H + 90})">')
    _ci_uncertainty(f, rows)
    f.raw('</g>')
    f.save()
    return {"rows": {r["trs"]: (r["ka"], r["unc"]) for r in rows}, "sites": len(sites), "arch": len(arch)}


CRMBOX = {"CIDOC CRM": "#d4e1f5", "CRMsci": "#ffcc99", "CRMarchaeo": "#e3d5f0", "CRMgeo": "#d9ead3"}


def _crm(col):
    return (col, "#000000", "#000000")


def workflow(D: AY.ArchData) -> dict:
    """Fig. 14 of the slides for the paper: datasets, one pipeline, a CRM-anchored graph, publication."""
    W_, H = 1700, 900
    f = Fig("paper-workflow", "geo-lod: from three datasets through one pipeline to a CIDOC CRM based graph and its publication", W_, H, OUT)
    cols = ((20, 340, "Datasets"), (520, 250, "Pipeline"), (910, 420, "Graph"), (1470, 220, "Publication"))
    for x, w, t in cols:
        _t(f, x + w / 2, 40, t, 32, True)
    ys = (190, 340, 490)
    for y, (a, b) in zip(ys, (("EPICA Dome C", "ice core"), ("SISAL", "speleothems"), ("CI findspots", "tephra"))):
        f.box(20, y, 340, 120, a, b, INST, 28, 24)
    f.box(520, 290, 250, 220, "Python", "one pipeline", INST, 30, 24)
    for y in ys:
        f.line(360, y + 60, 518, 400, "a")
    chip(f, 440, 400, "reads", 24)
    f.rect(905, 120, 430, 540, GL[0], "#000000", 14, 1.2)
    _t(f, 1120, 160, "Semantic graph", 28, True)
    f.box(920, 190, 400, 80, "CIDOC CRM", None, _crm(CRMBOX["CIDOC CRM"]), 26, 24, rx=10)
    for x, w_, a in ((920, 112, "CRMsci"), (1040, 168, "CRMarchaeo"), (1216, 104, "CRMgeo")):
        f.box(x, 300, w_, 80, a, None, _crm(CRMBOX[a]), 22, 24, rx=10)
    f.box(920, 500, 400, 130, "Domain layer", "geo-lod", ST, 28, 24, rx=10)
    f.line(1120, 498, 1120, 382, "a"); chip(f, 1120, 440, "anchored in the CRM family", 24)
    f.line(770, 400, 903, 400, "a"); chip(f, 836, 400, "builds", 24)
    f.box(905, 740, 430, 110, "Wikidata", None, TERM, 30, 24)
    f.line(1120, 662, 1120, 738, "a"); chip(f, 1120, 700, "links to", 24)
    for y, a in zip(ys, ("Documentation", "SPARQL page", "Turtle, figures")):
        f.box(1470, y, 220, 120, a, None, OWL, 26, 24)
        f.line(1335, y + 60, 1468, y + 60, "a")
    chip(f, 1400, 400 - 0, "serves", 24)
    f.save()
    return {}


def crm_family(D: AY.ArchData) -> dict:
    """Fig. 15 of the slides for the paper: the geo-lod layer between the CRM family and W3C standards, and its graph."""
    W_, H = 1400, 980
    f = Fig("paper-crm-family", "The geo-lod layer between the CIDOC CRM family and W3C standards, and the knowledge graph it produces", W_, H, OUT)
    f.rect(20, 20, 930, 250, "#eef2f9", "#000000", 14, 1)
    _t(f, 50, 52, "CRM family", 28, True, anchor="start")
    f.box(40, 76, 890, 70, "CIDOC CRM", "events, things, places, time, types", _crm(CRMBOX["CIDOC CRM"]), 26, 22, rx=10)
    for x, a, b in ((40, "CRMsci", "scientific observation"), (343, "CRMarchaeo", "excavation"), (646, "CRMgeo", "spatial reference")):
        f.box(x, 164, 284, 88, a, b, _crm(CRMBOX[a]), 26, 22, rx=10)
    f.rect(20, 360, 930, 230, "#f6f6f2", "#000000", 14, 1.4)
    _t(f, 50, 392, "Domain layer geo-lod", 28, True, anchor="start")
    X = (40, 343, 646)
    for x, (a, b, st) in zip(X, (("Geoscience", "cores, ages", GL), ("Stratigraphy", "units, boundaries", ST), ("Analysis", "specimens, methods", AN))):
        f.box(x, 424, 284, 130, a, b, st, 27, 22, rx=12)
    for x in X:
        f.line(x + 142, 358, x + 142, 272, "a")
    chip(f, X[1] + 142, 315, "anchored in the CRM family", 22)
    f.box(20, 680, 930, 100, "W3C and community standards", "SOSA/SSN, OWL-Time, GeoSPARQL, PROV-O, SKOS, DCAT", W3, 26, 22, rx=10)
    for x in X:
        f.line(x + 142, 592, x + 142, 678, "a")
    chip(f, X[1] + 142, 635, "reused, not copied", 22)
    f.rect(1080, 20, 300, 760, "#ffffff", "#000000", 14, 1.4)
    _t(f, 1230, 58, "Knowledge graph", 26, True, maxw=280)
    nodes = [(1230, 400, 28, INST), (1150, 270, 19, INST), (1310, 260, 19, TERM), (1150, 540, 19, INST), (1310, 520, 19, TERM),
             (1230, 660, 19, TERM), (1117, 410, 14, INST), (1345, 400, 14, TERM), (1230, 190, 14, INST)]
    for a, b in ((0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (1, 8), (1, 6), (3, 6), (2, 7), (4, 7)):
        f.raw(f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}" stroke="#555555" stroke-width="2"/>')
    for x, y, r, st in nodes:
        f.raw(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{st[0]}" stroke="#000000" stroke-width="1.4"/>')
    f.line(950, 470, 1078, 470, "a"); chip(f, 1014, 470, "builds", 22)
    f.rect(20, 860, 1360, 110, "#f1ecf8", "#000000", 14, 1.4)
    _t(f, 50, 880, "Federated Knowledge Graph Ecosystem", 24, True, anchor="start")
    for x, a in ((40, "RDF graphs"), (330, "Wikibase"), (620, "FDO data")):
        f.box(x, 900, 260, 56, a, None, OWL, 24, 22, rx=10)
    f.box(1030, 900, 330, 56, "Other knowledge graphs", None, TERM, 24, 22, rx=10)
    f.line(880, 928, 1028, 928, "a"); chip(f, 954, 928, "linked", 22)
    f.line(1230, 782, 1230, 858, "a"); chip(f, 1230, 820, "linked", 22)
    f.save()
    return {}


def linked_graph(D: AY.ArchData) -> dict:
    """Fig. 16 of the slides for the paper: one stalagmite as a node and what the graph links it to. PeriodO is planned."""
    import build as B
    W_, H = 1500, 880
    f = Fig("paper-linked-graph", "Where the graph opens up: a stalagmite as a node, linked to the CIDOC CRM family, its cave, Wikidata, DOIs, ORCID and its repository", W_, H, OUT)
    f.box(520, 20, 460, 100, "PeriodO", "period of the age, planned", TERM, 26, 22, dash=True)
    f.box(20, 150, 360, 110, "CIDOC CRM family", "class of the node", CLS, 26, 22)
    f.box(20, 730, 360, 110, "Wikidata, OSM", "the same place", TERM, 26, 22)
    f.box(1120, 150, 360, 110, "PANGAEA, Zenodo", "DOI of the dataset", TERM, 26, 22)
    f.box(1120, 340, 360, 110, "ORCID", "creators of the data", TERM, 26, 22)
    f.box(1120, 530, 360, 110, "Repository", "code and data", OWL, 26, 22)
    f.box(520, 730, 460, 110, "GeoSPARQL geometry", "coordinates of the cave", INST, 26, 22)
    B.stalagmite_glyph(f, 750, 500, 0.8, 0.3)
    _t(f, 750, 540, "Stalagmite", 34, True)
    _t(f, 750, 578, "one node, one persistent URI", 22, color=MUTED, maxw=330)
    B.cave_glyph(f, 200, 505, 1.0)
    _t(f, 200, 545, "Cave", 30, True)
    _t(f, 200, 580, "place of the stalagmite", 22, color=MUTED, maxw=340)
    for (x1, y1, x2, y2, t, cx, cy, d) in (
            (690, 330, 382, 215, "rdf:type", 536, 272, False),
            (690, 440, 372, 440, "located in", 531, 440, False),
            (200, 600, 200, 728, "owl:sameAs", 200, 664, False),
            (810, 330, 1118, 215, "owl:sameAs", 964, 272, False),
            (815, 395, 1118, 395, "dct:creator", 966, 395, False),
            (800, 450, 1118, 585, "prov:wasDerivedFrom", 984, 528, False),
            (750, 600, 750, 728, "geo:hasGeometry", 750, 664, False),
            (750, 252, 750, 122, "references period", 750, 187, True)):
        f.line(x1, y1, x2, y2, "a", dash=d)
        B.chip(f, cx, cy, t, 24)
    f.save()
    return {}


def _stalagmite_ticks(f, cx, by, sx, sy, depths, dmax, mark=None):
    """The stalagmite glyph of the slides with a tick at every dated depth, clipped to its outline.
    Returns a function from depth (mm) to the y position of that depth on the glyph."""
    Y = lambda d: 158 + 3.3 * d
    st = f"M 62 {Y(230)} C 85 640 110 260 122 {Y(10)} C 132 {Y(-16)} 188 {Y(-16)} 198 {Y(10)} C 210 260 235 640 258 {Y(230)} Z"
    tf = f"translate({cx - 160 * sx:.1f} {by - Y(230) * sy:.1f}) scale({sx} {sy})"
    g0, g1 = Y(-6), Y(230) - 24
    gy = lambda d_: g0 + (g1 - g0) * d_ / dmax
    f.raw(f'<g transform="{tf}"><clipPath id="sttick"><path d="{st}"/></clipPath><g clip-path="url(#sttick)">'
          f'<rect x="50" y="60" width="220" height="900" fill="url(#warm)"/>')
    for y in range(250, 930, 62):
        f.raw(f'<path d="M 50 {y + 28} Q 160 {y - 28} 270 {y + 28}" fill="none" stroke="#6b6a63" stroke-width="1.2" vector-effect="non-scaling-stroke"/>')
    for d_ in depths:
        hot = mark is not None and abs(d_ - mark) < 1e-6
        f.raw(f'<line x1="50" y1="{gy(d_):.1f}" x2="270" y2="{gy(d_):.1f}" stroke="{"#dc2626" if hot else "#000000"}" '
              f'stroke-width="{4.5 if hot else 2.2}" vector-effect="non-scaling-stroke"/>')
    f.raw(f'</g><path d="{st}" fill="none" stroke="#000000" stroke-width="2" vector-effect="non-scaling-stroke"/></g>')
    return lambda d_: by + (gy(d_) - Y(230)) * sy, lambda d_: (by + (g0 - Y(230)) * sy)


def _count(g, s, *preds):
    return sum(len(list(g.objects(s, p))) for p in preds)


def epica_instance(D: AY.ArchData) -> dict:
    """Fig. 4 for the paper. Panel a: one methane observation with the classes around it and the core drawn beside it,
    its MIS 1 to 6 bands read from the graph. Panel b: the catalogue with its two datasets, their sources, chronologies
    and smoothing, and where the core comes from."""
    import re
    import build as B
    from rdflib import Graph, Namespace, URIRef
    from rdflib.namespace import RDF, RDFS
    L = Namespace("http://w3id.org/geo-lod/")
    E = Namespace("http://w3id.org/geo-lod/epica/")
    g = Graph()
    g.parse(D.repo / "EPICA/rdf/epica_dome_c.ttl", format="turtle")
    begins = {}
    for a in g.subjects(RDF.type, L.MISAttributeAssignment):
        m = re.match(r"Beginning of MIS (\d+) at ([\d.]+) m in the CH4 record", str(g.value(a, RDFS.label)))
        if m and int(m.group(1)) <= 6:
            begins[int(m.group(1))] = float(m.group(2))
    o = E["obs_ch4_0371"]
    depth = float(g.value(o, L.atDepth_m))
    ppb = float(g.value(o, L.measuredValue))
    age = float(g.value(o, L.ageKaBP))
    stage = str(g.value(o, L.fallsWithinStage)).rsplit("_", 1)[-1]
    assert sorted(begins) == [1, 2, 3, 4, 5, 6] and stage == "5", (begins, stage)
    # panel b facts
    ds = {k: E[f"dataset_{k}"] for k in ("ch4", "d18o")}
    n_obs = {k: _count(g, ds[k], L.hasObservation, L.record) for k in ds}
    from rdflib.namespace import DCTERMS
    src = {k: g.value(ds[k], DCTERMS.source) for k in ds}
    src_label = {k: str(g.value(src[k], RDFS.label)).replace("&", "&") for k in ds}
    pang = {k: str(g.value(src[k], DCTERMS.source)).rsplit(".", 1)[-1] for k in ds}
    chron = {k: str(g.value(ds[k], L.ageChronology)).rsplit("/", 1)[-1] for k in ds}
    def _unit(prop):
        for pr, ob in g.predicate_objects(prop):
            if str(pr).rsplit("/", 1)[-1].rsplit("#", 1)[-1] == "unit":
                return str(ob).rsplit("/", 1)[-1]
        raise ValueError(f"{prop}: no unit")
    unit = {"ch4": _unit(E.property_ch4), "d18o": _unit(E.property_d18o)}
    assert unit == {"ch4": "PPB", "d18o": "PERMILLE"}, unit
    filt = [(g.value(o, L.smoothingMethod_rollingMedian), g.value(o, L.smoothingMethod_savgol))]
    rm, sg = filt[0]
    win = int(g.value(rm, L.windowSize)); order = int(g.value(sg, L.polyOrder)); win2 = int(g.value(sg, L.windowSize))
    assert (win, order, win2) == (11, 2, 11) and (pang["ch4"], pang["d18o"]) == ("472484", "961024") and chron == {"ch4": "EDC2-gas", "d18o": "AICC2023-gas"}
    wkt = str(g.value(g.value(E.site_dome_c, URIRef('http://www.opengis.net/ont/geosparql#hasGeometry')), URIRef("http://www.opengis.net/ont/geosparql#asWKT")))
    lon, lat = re.search(r"POINT\(([-\d.]+) ([-\d.]+)\)", wkt).groups()
    camp = str(g.value(E.campaign_1996_2004, RDFS.label)).rsplit(" ", 1)[-1]

    HA, HB = 940, 880
    W_ = 1700
    f = Fig("paper-epica-instance", "One methane observation of the EPICA Dome C ice core, and the catalogue, datasets and core behind it",
            W_, 70 + HA + 90 + HB, OUT)
    _panel_title(f, 36, "a", "One methane observation and the classes it is linked to")
    f.raw('<g transform="translate(0,70)">')
    cx0, cw, y0, y1, dmax = 50, 90, 100, 880, begins[6]
    Yd = lambda d_: y0 + d_ / dmax * (y1 - y0)
    _t(f, cx0 + cw / 2 + 30, 52, "EPICA Dome C", 24, True, maxw=190)
    edges = [0.0] + [begins[k] for k in range(1, 7)]
    for k in range(1, 7):
        fill = "url(#warm)" if k % 2 else "url(#cold)"
        f.rect(cx0, Yd(edges[k - 1]), cw, Yd(edges[k]) - Yd(edges[k - 1]), fill, "#000000", 0, 1)
        _t(f, cx0 + cw + 12, (Yd(edges[k - 1]) + Yd(edges[k])) / 2, f"MIS {k}", 22, color=MUTED, anchor="start")
    f.rect(cx0, y0, cw, y1 - y0, "none", "#000000", 4, 2.5)
    my = Yd(depth)
    f.raw(f'<circle cx="{cx0 + cw / 2}" cy="{my:.1f}" r="11" fill="#dc2626" stroke="#000000" stroke-width="2"/>')
    _t(f, cx0 + cw / 2, y1 + 34, f"{depth:,.0f} m", 24, True)
    cwid, ox, ocol = 260, 790, 1330
    f.box(230, 40, cwid, 100, "DataSource", "Spahni & Stocker 2006", ST, 26, 22)
    f.box(230, 365, cwid, 100, "IceCore", "EPICA Dome C core", ST, 26, 22)
    f.box(230, 740, cwid, 110, "DrillingSite", "EPICA Dome C", ST, 26, 22)
    f.box(ox, 40, 330, 100, "ObservableProperty", "Methane (CH₄), ppbv", ST, 26, 22)
    f.box(ox, 350, 330, 130, "IceCoreObservation", f"{ppb:.1f} ppbv at {depth:.3f} m", ST, 28, 22)
    f.box(ox, 740, 330, 110, "time:TimePosition", f"{age:.2f} ka on EDC2-gas", W3, 26, 22)
    f.box(ocol, 40, 330, 100, "MarineIsotopeStage", f"MIS {stage}, warm stage", ST, 26, 22)
    f.box(ocol, 215, 330, 100, "MISMembershipAssignment", f"observation falls in MIS {stage}", ST, 22, 22)
    f.box(ocol, 365, 330, 100, "IceCoreChronology", "EDC2-gas", ST, 26, 22)
    for (x1, y1_, x2, y2, t, cx, cy) in (
            (790, 360, 492, 142, "prov:wasDerivedFrom", 641, 251),
            (955, 350, 955, 142, "sosa:observedProperty", 955, 246),
            (790, 415, 492, 415, "hasFeatureOfInterest", 641, 415),
            (790, 470, 492, 742, "P7 took place at", 641, 606),
            (955, 480, 955, 738, "hasTimePosition", 955, 609),
            (1120, 415, 1328, 415, "ageChronology", 1224, 415),
            (1328, 270, 1122, 372, "P140 assigned to", 1225, 321),
            (1495, 215, 1495, 142, "P141 assigned", 1495, 178),
            (360, 467, 360, 738, "extractedFrom", 360, 602)):
        f.line(x1, y1_, x2, y2, "a")
        B.chip(f, cx, cy, t, 24)
    f.raw('</g>')
    _panel_title(f, 70 + HA + 50, "b", "The catalogue, its two datasets and the core behind them")
    f.raw(f'<g transform="translate(0,{70 + HA + 90})">')
    cat = (20, 170); dsx, dsw = 400, 250; rx, rw = 880, 310; sx_, sw = 1450, 240
    f.box(cat[0], 250, cat[1], 130, "Catalogue", "dcat:Catalog", ST, 26, 22)
    names = {"ch4": ("methane (CH4)", "%d values, %s"), "d18o": ("d18O of O2", "%d values, %s")}
    for r, k in enumerate(("ch4", "d18o")):
        yr = r * 340
        f.box(dsx, yr + 90, dsw, 130, "IceCoreDataset", names[k][0], ST, 26, 22)
        f.line(cat[0] + cat[1], 315, dsx - 2, yr + 155, "a")
        B.chip(f, (cat[0] + cat[1] + dsx) / 2, (315 + yr + 155) / 2, "dcat:dataset", 22)
        boxes = (("source", f"{src_label[k]}", f"DataSource, PANGAEA {pang[k]}", ST),
                 ("ageChronology", chron[k], "age chronology (TRS)", W3),
                 ("hasObservation", "IceCoreObservation", names[k][1] % (n_obs[k], unit[k]), ST))
        for i, (lab, t, sub, st) in enumerate(boxes):
            by = yr + i * 110
            f.box(rx, by, rw, 90, t, sub, st, 26, 22)
            f.line(dsx + dsw, yr + 155, rx - 2, by + 45, "a")
            B.chip(f, (dsx + dsw + rx) / 2, (yr + 155 + by + 45) / 2, lab, 22)
        if k == "ch4":
            for j, (lab, t, sub) in enumerate((("smoothingMethod", "Rolling median", f"window {win}"),
                                               ("smoothingMethod", "Savitzky-Golay", f"window {win2}, order {order}"))):
                by = 150 + j * 130 - 20
                f.box(sx_, by, sw, 90, t, sub, ST, 26, 22)
                f.line(rx + rw, yr + 2 * 110 + 45, sx_ - 2, by + 45, "a")
                B.chip(f, (rx + rw + sx_) / 2, (yr + 2 * 110 + 45 + by + 45) / 2, lab, 22)
    yc = 730
    chain = ((20, 280, "DrillingCampaign", camp, ST), (500, 280, "IceCore", "EPICA Dome C core", ST),
             (980, 280, "DrillingSite", "EPICA Dome C", ST), (1460, 240, "sf:Point", f"POINT({float(lon):g} {float(lat):g})", W3))
    for i, (x, w, t, sub, st) in enumerate(chain):
        f.box(x, yc, w, 110, t, sub, st, 26, 22)
    for (x0, x1, lab) in ((300, 500, "O1_removed"), (780, 980, "extractedFrom"), (1260, 1460, "hasGeometry")):
        f.line(x0, yc + 55, x1 - 2, yc + 55, "a")
        B.chip(f, (x0 + x1) / 2, yc + 55, lab, 22)
    f.raw('</g>')
    f.save()
    return {"depth": depth, "ppbv": ppb, "age": age, "stage": stage, "begins": begins, "obs": n_obs, "wkt": wkt}


def sisal_instance(D: AY.ArchData) -> dict:
    """Fig. 5 for the paper. Panel a: the cave site Chauvet with what the annotation adds. Panel b: one speleothem as a
    stalagmite with a tick at every dated depth, one age control point with its dating method, age models and source,
    the hiatus, and the dating points by depth and age. The parts only the pipeline writes are dashed."""
    import re
    import build as B
    from rdflib import Graph, Namespace, URIRef
    from rdflib.namespace import RDF, RDFS
    L = Namespace("http://w3id.org/geo-lod/")
    S = Namespace("http://w3id.org/geo-lod/sisal/")
    g = Graph()
    for name in ("sisal_v3_dating", "sisal_sites", "sisal_site_annotations"):
        g.parse(D.repo / f"SISAL/rdf/{name}.ttl", format="turtle")
    # --- panel a facts
    cave = L["Cave_site_0077"]
    cls = {str(t).rsplit("/", 1)[-1] for t in g.objects(cave, RDF.type)}
    assert {"Cave", "ArchaeologicalCaveSite"} <= cls
    label = str(g.value(cave, RDFS.label))
    n18, n13 = int(g.value(cave, L.countD18OSamples)), int(g.value(cave, L.countD13CSamples))
    elev = float(g.value(cave, L.elevation_m))
    cat_, conf = str(g.value(cave, L.archaeologicalCategory)), str(g.value(cave, L.archaeologicalConfidence))
    wd = str(g.value(cave, URIRef("http://www.w3.org/2002/07/owl#sameAs"))).rsplit("/", 1)[-1]
    unesco = str(g.value(cave, L.unescoWHId)).rsplit("/", 1)[-1]
    ctx = str(g.value(cave, L.archaeologicalBroaderContext)).rsplit("/", 1)[-1]
    wkt = str(g.value(g.value(cave, URIRef('http://www.opengis.net/ont/geosparql#hasGeometry')), URIRef("http://www.opengis.net/ont/geosparql#asWKT")))
    lon, lat = re.search(r"POINT\(([-\d.]+) ([-\d.]+)\)", wkt).groups()
    n_cave = len(list(g.objects(L.SISAL_Cave_Collection, RDFS.member)))
    n_arch = len(list(g.objects(L.SISAL_Archaeological_Cave_Collection, RDFS.member)))
    assert (n18, n13, wd, unesco) == (210, 210, "Q191483", "1426"), (n18, n13, wd, unesco)
    # --- panel b facts
    ent = S["entity_00055"]
    pts = []
    for dp in g.subjects(L.constrainsSpeleothem, ent):
        pts.append((float(g.value(dp, L.atDepth_mm)), float(g.value(dp, L.ageKaBP)), float(g.value(dp, L.ageUncertaintyPos_ka)), dp))
    pts.sort(key=lambda r: r[0])
    hi = next(p_ for p_ in pts if str(p_[3]).endswith("datingpoint_000942"))
    models = sorted(str(m).rsplit("AgeModel_", 1)[-1] for m in g.objects(hi[3], L.usedInAgeModel))
    method = str(g.value(hi[3], L.datingMethod)).rsplit("DatingMethod_", 1)[-1]
    assert method == "u_th_unspecified", method
    hiat = [float(g.value(h, L.atDepth_mm)) for h in g.subjects(L.inSpeleothem, ent) if (h, RDF.type, L.GrowthHiatus) in g]
    assert len(hiat) == 1, hiat
    names = {"bacon": "Bacon", "bchron": "Bchron", "copra": "COPRA", "lin_interp": "linear interpolation", "oxcal": "OxCal", "stalage": "StalAge"}
    assert set(models) == set(names), models

    HA, HB = 640, 1060
    f = Fig("paper-sisal-instance", "The cave site Chauvet and one SISAL speleothem with its dating points", 1700, 70 + HA + 90 + HB, OUT)
    _panel_title(f, 36, "a", "A cave site, enriched with the archaeological annotation")
    f.raw('<g transform="translate(0,70)">')
    B.cave_glyph(f, 190, 470, 1.15)
    f.box(360, 20, 390, 90, "SISAL cave collection", f"{n_cave} caves", GL, 26, 22)
    f.box(830, 20, 400, 90, "Archaeological cave collection", f"{n_arch} caves, archaeological record", GL, 24, 22)
    sx0, sy0, sw0, sh0 = 480, 230, 440, 250
    f.rect(sx0, sy0, sw0, sh0, ST[0], "#000000", 6, 1)
    _t(f, sx0 + sw0 / 2, sy0 + 36, label, 30, True)
    for i, (t, c) in enumerate(((" , ".join(["Cave", "ArchaeologicalCaveSite"]).replace(" , ", ", "), None),
                                ("Cave_site_0077, %g m" % elev, None),
                                (f"δ18O {n18}, δ13C {n13} samples", None),
                                (f"{cat_}, confidence {conf}", MUTED))):
        _t(f, sx0 + sw0 / 2, sy0 + 82 + i * 38, t, 22, color=c)
    for (x1, y1_, x2, y2) in ((555, 112, 600, 228), (1030, 112, 820, 228)):
        f.line(x1, y1_, x2, y2, "a")
        B.chip(f, (x1 + x2) / 2, (y1_ + y2) / 2, "rdfs:member", 22)
    rx, rw = 1290, 380
    right = (("owl:sameAs", f"wd:{wd}", "Wikidata", OWL), ("unescoWHId", "UNESCO World Heritage", f"whc.unesco.org/en/list/{unesco}", OWL),
             ("archaeologicalBroaderContext", ctx, "ArchaeologicalContext", TERM), ("hasGeometry", "sf:Point", f"POINT({float(lon):g} {float(lat):g})", W3),
             ("prov:wasDerivedFrom", "DataSource", "SISAL v3, site annotations", OWL))
    for i, (lab, t, sub, st) in enumerate(right):
        by = 50 + i * 118
        f.box(rx, by, rw, 92, t, sub, st, 26, 22)
        y_from = sy0 + 40 + i * 42
        f.line(sx0 + sw0, y_from, rx - 2, by + 46, "a")
        B.chip(f, (sx0 + sw0 + rx) / 2 + (i - 2) * 10, (y_from + by + 46) / 2, lab, 22)
    f.raw('</g>')
    _panel_title(f, 70 + HA + 50, "b", "One speleothem of that cave strand, its dating points and age models")
    f.raw(f'<g transform="translate(0,{70 + HA + 90})">')
    dmax = max(p_[0] for p_ in pts) * 1.06
    gcx, gby = 180, 700
    ypos, _top = _stalagmite_ticks(f, gcx, gby, 1.15, 0.68, [p_[0] for p_ in pts], dmax, mark=hi[0])
    _t(f, gcx, 40, "Speleothem", 30, True)
    _t(f, gcx, 76, "sisal:entity_00055", 22, color=MUTED)
    _t(f, gcx, gby + 36, "ticks mark the dated depths", 22, color=MUTED)
    bx, bw = 620, 330
    f.box(bx, 90, bw, 150, "AgeControlPoint", f"{hi[1]:.3f} ± {hi[2]:.3f} ka", ST, 28, 24)
    _t(f, bx + bw / 2, 208, f"at {hi[0]:.1f} mm", 22)
    f.line(bx, 165, gcx + 75, ypos(hi[0]), "a")
    B.chip(f, 440, (165 + ypos(hi[0])) / 2, "constrainsSpeleothem", 22)
    f.box(bx, 330, bw, 150, "GrowthHiatus", f"at {hiat[0]:.1f} mm", ST, 26, 22)
    _t(f, bx + bw / 2, 446, "respected by all 6 models", 22, color=MUTED)
    f.line(bx, 395, gcx + 75, ypos(hiat[0]), "a")
    B.chip(f, 440, (395 + ypos(hiat[0])) / 2, "inSpeleothem", 22)
    f.rect(bx, 530, bw, 130, "#ffffff", "#000000", 6, 2.2, dash=True)
    _t(f, bx + bw / 2, 566, "SpeleothemSample", 26, True)
    _t(f, bx + bw / 2, 602, "δ18O and δ13C observations", 22)
    _t(f, bx + bw / 2, 634, "pipeline only", 22, color=MUTED)
    f.line(bx, 595, gcx + 95, ypos(dmax * 0.9), "a", dash=True)
    B.chip(f, 440, (595 + ypos(dmax * 0.9)) / 2, "collectedFrom", 22)
    cx, cw = 1340, 330
    f.box(cx, 40, cw, 100, "DatingMethod", "U/Th, unspecified", TERM, 26, 22)
    f.rect(cx, 230, cw, 200, ST[0], "#000000", 6, 1)
    _t(f, cx + cw / 2, 264, "AgeModel", 26, True)
    _t(f, cx + cw / 2, 302, f"{len(models)} age models", 22)
    for i, line in enumerate(("Bacon, Bchron, COPRA,", "linear interpolation,", "OxCal, StalAge")):
        _t(f, cx + cw / 2, 342 + i * 30, line, 22, color=MUTED, maxw=cw - 20)
    f.box(cx, 500, cw, 100, "DataSource", "SISAL v3", OWL, 26, 22)
    for (y2, t) in ((90, "datingMethod"), (330, "usedInAgeModel"), (550, "prov:wasDerivedFrom")):
        f.line(bx + bw, 165, cx - 2, y2, "a")
        B.chip(f, (bx + bw + cx) / 2, (165 + y2) / 2, t, 22)
    px0, px1, py0, py1 = 560, 1500, 790, 940
    f.rect(px0 - 80, py0 - 80, px1 - px0 + 150, py1 - py0 + 170, "#ffffff", "#bdbbb2", 10, 1)
    _t(f, (px0 + px1) / 2, py0 - 50, f"{len(pts)} dating points of this speleothem", 24, True, maxw=560)
    a1 = math.ceil(max(p_[1] for p_ in pts))
    Xp = lambda d_: px0 + d_ / dmax * (px1 - px0)
    Yp = lambda a_: py1 - a_ / a1 * (py1 - py0)
    f.line(px0, py1, px1, py1, None, w=1.6, color="#555555")
    f.line(px0, py0, px0, py1, None, w=1.6, color="#555555")
    for a_ in (0, 10, 20):
        if a_ <= a1:
            f.line(px0 - 6, Yp(a_), px0, Yp(a_), None, w=1.6, color="#555555")
            _t(f, px0 - 14, Yp(a_), f"{a_}", 22, color=MUTED, anchor="end")
    for d_ in (0, 400, 800, 1200):
        if d_ <= dmax:
            f.line(Xp(d_), py1, Xp(d_), py1 + 6, None, w=1.6, color="#555555")
            _t(f, Xp(d_), py1 + 28, f"{d_}", 22, color=MUTED)
    _t(f, (px0 + px1) / 2, py1 + 58, "depth from the top (mm)", 22, color=MUTED)
    _t(f, px0 - 14, py0 - 18, "age (ka BP)", 22, color=MUTED, anchor="start")
    f.line(Xp(hiat[0]), py0, Xp(hiat[0]), py1, None, dash=True, w=1.8, color="#555555")
    _t(f, Xp(hiat[0]) - 10, py0 + 14, "hiatus", 22, color=MUTED, anchor="end")
    for d_, a_, u_, dp in pts:
        is_hi = dp == hi[3]
        f.raw(f'<circle cx="{Xp(d_):.1f}" cy="{Yp(a_):.1f}" r="{9 if is_hi else 6}" fill="{"#dc2626" if is_hi else "#0072B2"}" stroke="#000000" stroke-width="1.2"/>')
    f.raw('</g>')
    f.save()
    return {"points": len(pts), "models": models, "method": method, "hiatus": hiat, "collections": (n_cave, n_arch)}


def ci_map(D: AY.ArchData) -> dict:
    """Fig. 8 for the paper: the CI findspots of the selection on a map, the archaeological ones numbered by distance from the
    source and listed beneath, read from the committed graph."""
    import re
    import build as B
    from rdflib import Namespace
    L = Namespace("http://w3id.org/geo-lod/")
    ci = D.ci
    lon0, lon1, lat0, lat1 = 5.0, 50.0, 31.5, 53.0
    Wm = 1700
    kx = Wm / (lon1 - lon0)
    ky = kx / math.cos(math.radians(43))
    Hm = round((lat1 - lat0) * ky)
    legend_h = 335
    f = Fig("paper-ci-map", "Campanian Ignimbrite findspots of the selection, with the archaeological sites numbered by distance from the source",
            Wm, Hm + legend_h, OUT)
    px = lambda lon: (lon - lon0) * kx
    py = lambda lat: (lat1 - lat) * ky
    f.rect(0, 0, Wm, Hm, "#dcebf2")
    d = " ".join("M " + " L ".join(f"{px(a):.1f} {py(b):.1f}" for a, b in r) + " Z" for r in B.land_rings())
    f.raw(f'<defs><clipPath id="mapclip"><rect x="0" y="0" width="{Wm}" height="{Hm}"/></clipPath></defs><g clip-path="url(#mapclip)">')
    f.raw(f'<path d="{d}" fill="#f4f1e8" fill-rule="evenodd" stroke="#b9b4a8" stroke-width="1"/>')
    src = (14.1402, 40.8275)
    for rk in (500, 1000, 1500, 2000):
        pts, dd = [], rk / 6371.0088
        for i in range(181):
            b = math.radians(i * 2); p0 = math.radians(src[1])
            la = math.asin(math.sin(p0) * math.cos(dd) + math.cos(p0) * math.sin(dd) * math.cos(b))
            lo = math.radians(src[0]) + math.atan2(math.sin(b) * math.sin(dd) * math.cos(p0), math.cos(dd) - math.sin(p0) * math.sin(la))
            pts.append((px(math.degrees(lo)), py(math.degrees(la))))
        f.raw('<path d="M ' + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + ' Z" fill="none" stroke="#7a8a92" stroke-width="1.5" stroke-dasharray="6 7"/>')
        x, y = pts[100]
        _t(f, x + 6, y - 14, f"{rk} km", 22, color="#55666e", anchor="start")
    arch_set = {str(s_).rsplit("/", 1)[-1] for s_ in ci.subjects(RDF.type, L.CIArchaeologicalSite)}
    assert len(arch_set) == 12
    arch, others, eifel = [], [], []
    for local, lon, lat, level, typed, curated in D.findspots:
        if local == "cisite_22":
            continue
        if local in arch_set:
            label = re.sub(r" near .*$", "", re.sub(r" \(.*\)$", "", str(ci.value(AY.CI[local], AY.RDFS.label))))
            arch.append((AY.haversine_km(src, (lon, lat)) if hasattr(AY, "haversine_km") else _hav(src, (lon, lat)), local, lon, lat, level, label))
        elif 6.0 < lon < 7.2 and 50.0 < lat < 50.6:
            eifel.append((lon, lat, str(ci.value(AY.CI[local], AY.RDFS.label))))
        else:
            others.append((lon, lat))
    arch.sort()
    for lon, lat in others:
        if lon0 <= lon <= lon1 and lat0 <= lat <= lat1:
            f.raw(f'<circle cx="{px(lon):.1f}" cy="{py(lat):.1f}" r="9" fill="#ffffff" stroke="#5f5e5a" stroke-width="2"/>')
    EG = "#166534"
    ex, ey = px(sum(e[0] for e in eifel) / len(eifel)), py(sum(e[1] for e in eifel) / len(eifel))
    cx_, cy_ = ex + 58, ey + 40
    f.line(ex, ey, cx_, cy_, None, w=1.8, color="#1f1f1d")
    f.raw(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="9" fill="#ffffff" stroke="#5f5e5a" stroke-width="2"/><circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" fill="#1f1f1d"/>')
    f.raw(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="21" fill="{EG}" stroke="#000000" stroke-width="2"/>')
    _t(f, cx_, cy_ + 1, "E", 22, True, color="#ffffff")
    s0 = (px(src[0]), py(src[1]))
    f.raw('<polygon points="' + " ".join(f"{s0[0] + (22 if i % 2 == 0 else 9) * math.sin(i * math.pi / 5):.1f},{s0[1] - (22 if i % 2 == 0 else 9) * math.cos(i * math.pi / 5):.1f}" for i in range(10)) + '" fill="#4c1d95" stroke="#000000" stroke-width="1.5"/>')
    placed = [s0]
    R = 21
    out = []
    for n, (km_, local, lon, lat, level, label) in enumerate(arch, 1):
        x, y = px(lon), py(lat)
        best = None
        for rad in (0, 50, 76, 104, 134):
            for k in range(0 if rad == 0 else 24):
                ang = k * math.pi / 12 + 0.4
                cx, cy = (x, y) if rad == 0 else (x + rad * math.cos(ang), y + rad * math.sin(ang))
                if not (R + 4 < cx < Wm - R - 4 and R + 4 < cy < Hm - R - 4):
                    continue
                if all(math.hypot(cx - qx, cy - qy) > 2 * R + 16 for qx, qy in placed) and \
                        all(math.hypot(cx - px(a[2]), cy - py(a[3])) > R + 10 for a in arch if a[1] != local):
                    best = (cx, cy); break
            if best:
                break
        best = best or (x, y)
        placed.append(best)
        out.append((n, km_, local, x, y, best, level, label))
    for n, km_, local, x, y, (cx, cy), level, label in out:
        hollow = level in ("dubious", "low")
        fill, col = ("#ffffff", "#9a3412") if hollow else ("#9a3412", "#ffffff")
        if math.hypot(cx - x, cy - y) > 1:
            f.line(x, y, cx, cy, None, w=1.8, color="#1f1f1d")
            f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#1f1f1d"/>')
        f.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" fill="{fill}" stroke="#9a3412" stroke-width="3"/>')
        _t(f, cx, cy + 1, str(n), 22, True, color=col)
    f.raw('</g>')
    # legend beneath the map: three columns of four sites, then the symbols
    y0 = Hm + 40
    colw = 560
    for n, km_, local, x, y, _p, level, label in out:
        c, r = divmod(n - 1, 4)
        hollow = level in ("dubious", "low")
        fill, col = ("#ffffff", "#9a3412") if hollow else ("#9a3412", "#ffffff")
        lx, ly = 30 + c * colw, y0 + r * 46
        f.raw(f'<circle cx="{lx + R}" cy="{ly}" r="{R}" fill="{fill}" stroke="#9a3412" stroke-width="3"/>')
        _t(f, lx + R, ly + 1, str(n), 22, True, color=col)
        _t(f, lx + 58, ly, label, 22, True, anchor="start", maxw=300)
        _t(f, lx + colw - 40, ly, f"{km_:,.0f} km", 22, color=MUTED, anchor="end")
    eif = sorted(((_hav(src, (lo, la)), lab, i) for i, (lo, la, lab) in enumerate(eifel)), key=lambda t: (round(t[0]), t[1]))
    for k, (km_, lab, _i) in enumerate(eif):
        lx, ly = 30 + k * colw, y0 + 4 * 46
        f.raw(f'<circle cx="{lx + R}" cy="{ly}" r="{R}" fill="#166534" stroke="#000000" stroke-width="2"/>')
        _t(f, lx + R, ly + 1, f"E{k + 1}", 22, True, color="#ffffff")
        _t(f, lx + 58, ly, lab, 22, True, anchor="start", maxw=300)
        _t(f, lx + colw - 40, ly, f"{km_:,.0f} km", 22, color=MUTED, anchor="end")
    ly = y0 + 5 * 46 + 30
    f.raw('<polygon points="' + " ".join(f"{51 + (18 if i % 2 == 0 else 8) * math.sin(i * math.pi / 5):.1f},{ly - (18 if i % 2 == 0 else 8) * math.cos(i * math.pi / 5):.1f}" for i in range(10)) + '" fill="#4c1d95" stroke="#000000"/>')
    _t(f, 80, ly, "Phlegraean Fields, the source", 22, color=MUTED, anchor="start")
    f.raw(f'<circle cx="{30 + colw + 21}" cy="{ly}" r="9" fill="#ffffff" stroke="#5f5e5a" stroke-width="2"/>')
    _t(f, 30 + colw + 46, ly, f"{len(others)} other findspots", 22, color=MUTED, anchor="start")
    f.raw(f'<circle cx="{30 + 2 * colw + 21}" cy="{ly}" r="14" fill="#ffffff" stroke="#9a3412" stroke-width="3"/>')
    _t(f, 30 + 2 * colw + 46, ly, "certainty low or dubious", 22, color=MUTED, anchor="start", maxw=330)
    f.save()
    return {"arch": len(out), "eifel": [e[2] for e in eifel], "others": len(others), "named": [o[7] for o in out], "km": [round(o[1]) for o in out]}


def epica_series(D: AY.ArchData) -> dict:
    """Fig. 2a for the paper: the methane record of EPICA Dome C with the measured value and the two smoothed values,
    the whole record above and the first 60 ka below. Read from the committed graph; no title, the caption says the rest."""
    import cluster_measurement as MT
    M = MT.MeasData(D.repo)
    ser = M.series
    ages = [r[0] for r in ser]
    y_lo, y_hi = 300, 1000
    gapmin = 8 * sorted(b - a for a, b in zip(ages, ages[1:]))[len(ages) // 2]
    holes = [(a, b) for a, b in zip(ages, ages[1:]) if b - a > gapmin]
    W, H = 1700, 1040
    f = Fig("paper-epica-series", "EPICA Dome C methane: measured and smoothed values", W, H, OUT)
    left, right = 150, 1660
    RAW, MED, SAV = MT.RAW_COLOUR, MT.MEDIAN_COLOUR, MT.SAVGOL_COLOUR

    def panel(top, bottom, x0, x1, pts, title, dots, xtick, shade=()):
        X = lambda a: round(left + (right - left) * (a - x0) / (x1 - x0), 1)
        Y = lambda v: round(bottom - (v - y_lo) / (y_hi - y_lo) * (bottom - top), 1)
        _t(f, left, top - 34, title, 24, True, anchor="start")
        for a, b in shade:
            f.rect(X(a), top, round(X(b) - X(a), 1), bottom - top, "#f1efe8")
            _t(f, (X(a) + X(b)) / 2, (top + bottom) / 2, f"no observations, {a:.0f} to {b:.0f} ka BP", 22, color=MUTED, maxw=X(b) - X(a) - 20)
        for v in range(y_lo, y_hi + 1, 100):
            f.line(left, Y(v), right, Y(v), None, w=1, color="#d8d6ce")
            _t(f, left - 14, Y(v), str(v), 22, color=MUTED, anchor="end")
        t = math.ceil(x0 / xtick) * xtick
        while t <= x1 + 1e-9:
            f.line(X(t), bottom, X(t), bottom + 8, None, w=1.2, color=MUTED)
            _t(f, X(t), bottom + 32, f"{t:g}", 22, color=MUTED)
            t += xtick
        _t(f, right, bottom + 64, "age, ka BP", 22, color=MUTED, anchor="end")
        _t(f, left - 14, top - 34, "ppbv", 22, color=MUTED, anchor="end")
        if dots:
            for a, m, *_ in pts:
                f.raw(f'<circle cx="{X(a)}" cy="{Y(m)}" r="3" fill="{RAW}" fill-opacity=".75"/>')
        for k, colour in ((2, MED), (3, SAV)):
            d = " ".join(("M" if i == 0 or r[0] - pts[i - 1][0] > gapmin else "L") + f"{X(r[0])} {Y(r[k])}" for i, r in enumerate(pts))
            f.raw(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{2.8 if dots else 1.8}" stroke-linejoin="round"/>')
        return X, Y

    panel(80, 380, 0, ages[-1], ser, f"The whole record, {len(ser)} observations", False, 100, holes)
    near = [r for r in ser if r[0] <= 60.0]
    X, Y = panel(540, 880, 0, 60.0, near, f"The first 60 ka, {len(near)} observations", True, 10)
    a0, m0, med0, sg0, _ = near[0]
    items = sorted(((m0, f"measured {m0:g}", RAW), (sg0, f"Savitzky-Golay {sg0:.1f}", SAV), (med0, f"rolling median {med0:g}", MED)), key=lambda t: -t[0])
    for v, _txt, colour in items:
        f.raw(f'<circle cx="{X(a0)}" cy="{Y(v)}" r="7" fill="none" stroke="{colour}" stroke-width="2.6"/>')
    for i, (v, txt, colour) in enumerate(items):
        ly = 560 + i * 34
        f.line(X(a0) + 9, Y(v), left + 70, ly, None, w=1, color=MUTED)
        _t(f, left + 80, ly, f"first observation: {txt}", 22, color=colour if colour != RAW else "#4a4a46", anchor="start")
    ly = 990
    for i, (colour, text, dot) in enumerate(((RAW, "measured value", True), (MED, "rolling median, window 11", False), (SAV, "Savitzky-Golay, window 11, order 2", False))):
        x = left + [0, 380, 860][i]
        if dot:
            f.raw(f'<circle cx="{x + 12}" cy="{ly}" r="6" fill="{colour}" fill-opacity=".75"/>')
        else:
            f.line(x, ly, x + 28, ly, None, w=4, color=colour)
        _t(f, x + 42, ly, text, 22, color=MUTED, anchor="start")
    f.save()
    return {"n": len(ser), "near": len(near), "holes": holes, "first": (m0, med0, sg0)}


def mis_depths(D: AY.ArchData) -> dict:
    """Fig. 2b for the paper: the beginning of each marine isotope stage on the EPICA timescales it is dated on, one row per
    stage with its depth on each timescale and the spread between them. Read from the committed graphs."""
    import cluster_mis as MS
    M = MS.MisData(D.repo)
    stages = sorted({s for s, *_ in M.depths})
    order = MS.TRS_ORDER
    val = {(s, t): d for s, t, d, _ in M.depths}
    age = {s: a for s, _, _, a in M.depths}
    left, cell, rowh, top = 330, 190, 38, 120
    W = 1700
    H = top + rowh * len(stages) + 30
    f = Fig("paper-mis-depths", "Depth of the beginning of each marine isotope stage on the EPICA timescales", W, H, OUT)
    bx = left + cell * len(order) + 14
    for j, t in enumerate(order):
        cx = left + cell * j + cell / 2
        _t(f, cx, top - 70, M.trs_label[t].replace(" age", ""), 22, True, maxw=cell - 6)
        f.raw(f'<circle cx="{cx}" cy="{top - 34}" r="8" fill="{MS.TRS_COLOUR[t]}" stroke="#000000" stroke-width="1.5"/>')
    _t(f, 20, top - 70, "depth in m, by timescale", 22, color=MUTED, anchor="start")
    _t(f, left - 14, top - 34, "age of boundary", 22, color=MUTED, anchor="end")
    _t(f, bx, top - 70, "Spread", 22, True, anchor="start")
    _t(f, bx, top - 34, "between scales", 22, color=MUTED, anchor="start")
    spread = {s: max(val[(s, t)] for t in order if (s, t) in val) - min(val[(s, t)] for t in order if (s, t) in val) for s in stages}
    mx = max(spread.values())
    for i, s in enumerate(stages):
        y = top + i * rowh
        if i % 2 == 0:
            f.rect(10, y, W - 20, rowh, "#f6f6f3")
        _t(f, 20, y + rowh / 2, f"MIS {s}", 22, True, anchor="start")
        _t(f, left - 14, y + rowh / 2, f"{age[s]:g} ka BP", 22, color=MUTED, anchor="end")
        for j, t in enumerate(order):
            cx = left + cell * j + cell / 2
            if (s, t) in val:
                f.raw(f'<circle cx="{cx - 62}" cy="{y + rowh / 2}" r="7" fill="{MS.TRS_COLOUR[t]}" stroke="#000000" stroke-width="1.2"/>')
                _t(f, cx - 46, y + rowh / 2, f"{val[(s, t)]:.1f}", 22, anchor="start")
            else:
                _t(f, cx, y + rowh / 2, "\u00b7", 22, color="#b5b3aa")
        w_ = round(150 * spread[s] / mx, 1)
        f.rect(bx, y + 8, w_, rowh - 16, "#9a3412", "#000000", 0, 1)
        _t(f, bx + w_ + 8, y + rowh / 2, f"{spread[s]:.0f} m", 22, anchor="start")
    f.save()
    return {"stages": len(stages), "assignments": len(M.depths), "widest": max(stages, key=lambda s: spread[s])}


def sisal_map(D: AY.ArchData) -> dict:
    """Map for the paper: the SISAL caves of the committed graph on a world map, the archaeological ones and those that are
    UNESCO World Heritage set apart. Replaces map_sisal (which showed 305 points and no counts)."""
    import build as B
    import geo_lod_basemap as gb
    from rdflib import Namespace
    L = Namespace("http://w3id.org/geo-lod/")
    lon0, lon1, lat0, lat1 = -180.0, 180.0, -60.0, 85.0
    Wm = 1700
    k = Wm / (lon1 - lon0)
    Hm = round((lat1 - lat0) * k)
    f = Fig("paper-sisal-map", "SISAL caves of the graph by the oldest age of their samples with a time bar, the caves with a recorded archaeological use ringed", Wm, Hm + 345, OUT)
    px = lambda lon: (lon - lon0) * k
    py = lambda lat: (lat1 - lat) * k
    f.rect(0, 0, Wm, Hm, "#dcebf2")
    d = ""
    for ring in gb._rings_of(gb.land_path(str(REPO))):
        c = gb.clip_ring(ring, (lon0, lat0, lon1, lat1))
        if c and len(c) >= 3:
            t = gb.simplify(c, 0.15)
            if len(t) >= 3:
                d += "M " + " L ".join(f"{px(a):.1f} {py(b):.1f}" for a, b in t) + " Z "
    f.raw(f'<defs><clipPath id="wmap"><rect x="0" y="0" width="{Wm}" height="{Hm}"/></clipPath></defs><g clip-path="url(#wmap)">')
    f.raw(f'<path d="{d}" fill="#f4f1e8" fill-rule="evenodd" stroke="#b9b4a8" stroke-width="1"/>')
    for lo in range(-120, 121, 60):
        f.line(px(lo), 0, px(lo), Hm, None, w=1, color="#c8d3d8")
        _t(f, px(lo), Hm - 18, f"{lo}\u00b0", 22, color="#55666e")
    for la in (-30, 0, 30, 60):
        f.line(0, py(la), Wm, py(la), None, w=1, color="#c8d3d8")
        _t(f, 8, py(la) - 14, f"{la}\u00b0", 22, color="#55666e", anchor="start")
    caves = sorted(D.ss.subjects(RDF.type, L.Cave))
    arch = {str(c) for c in D.sa.subjects(RDF.type, L.ArchaeologicalCaveSite)}
    unesco = {str(c) for c in D.sa.subjects(L.isUNESCOWorldHeritage, None) if str(D.sa.value(c, L.isUNESCOWorldHeritage)).lower() == "true"}
    import cluster_mis as MS
    stages = {}
    for st_, _t_, _d, a_ in MS.MisData(D.repo).depths:
        stages[st_] = a_
    AX = 600.0                                      # the bar runs to 600 ka; older caves take the colour of its end
    sq = lambda a_: math.sqrt(max(0.0, min(a_, AX)) / AX)          # square-root axis: the recent stages stay readable
    STOPS = ((0.0, (0xf2, 0xc7, 0x44)), (0.25, (0x8c, 0xc0, 0x8a)), (0.5, (0x2a, 0x9d, 0x9a)), (0.75, (0x2b, 0x5f, 0x9e)), (1.0, (0x1c, 0x10, 0x49)))

    def ramp(t):
        for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
            if t <= t1:
                u = (t - t0) / (t1 - t0)
                return "#%02x%02x%02x" % tuple(round(a_ + (b_ - a_) * u) for a_, b_ in zip(c0, c1))
        return "#%02x%02x%02x" % STOPS[-1][1]

    rows = []
    for c in caves:
        lon, lat = AY._point(D.ss.value(D.ss.value(c, AY.GEO.hasGeometry), AY.GEO.asWKT))
        old, yng, nd = (D.ss.value(c, L.oldestAgeKaBP), D.ss.value(c, L.youngestAgeKaBP), D.ss.value(c, L.countDatedD18OSamples))
        rows.append((None if old is None else float(old), None if yng is None else float(yng), lon, lat, str(c) in arch or str(c) in unesco,
                     str(c) in unesco, int(nd) if nd is not None else 0, str(D.ss.value(c, AY.RDFS.label))))
    assert len(rows) == D.n_caves == len(caves)
    rad = lambda n_: 7.0
    for old, _y, lon, lat, _a, _u, nd, _l in sorted(rows, key=lambda r: (-1e9 if r[0] is None else -r[0])):   # the oldest first, so that the young ones lie on top
        x, y = px(lon), py(lat)
        if old is None:
            f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#ffffff" stroke="#5f5e5a" stroke-width="2"/>')
        else:
            f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad(nd):.1f}" fill="{ramp(sq(old))}" stroke="#2b2b29" stroke-width="1"/>')
    for _o, _y, lon, lat, a_, u_, nd, _l in rows:
        if a_:
            f.raw(f'<circle cx="{px(lon):.1f}" cy="{py(lat):.1f}" r="{rad(nd) + 5:.1f}" fill="none" stroke="#9a3412" stroke-width="3.5"/>')
    # callouts as on the CI map: a ringed location, a leader line and a numbered circle out in the Atlantic
    eif = [(lo, la) for lc, lo, la, *_ in D.findspots if lc != "cisite_22" and 6.0 < lo < 7.2 and 50.0 < la < 50.6]
    assert eif
    marks = [("E", sum(e[0] for e in eif) / len(eif), sum(e[1] for e in eif) / len(eif), "#166534"),
             ("1", *[(r[2], r[3]) for r in rows if r[7] == "Spannagel cave"][0], "#9a3412"),
             ("2", *[(r[2], r[3]) for r in rows if r[7] == "Piani Eterni karst system"][0], "#9a3412")]
    for i, (lab, lo, la, col) in enumerate(marks):
        x, y = px(lo), py(la)
        cx_, cy_ = px(-22.0), py(57.0 - 9.0 * i)
        f.line(cx_, cy_, x, y, None, w=1.8, color="#1f1f1d")
        f.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="none" stroke="#1f1f1d" stroke-width="2.2"/>')
        f.raw(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="21" fill="{col}" stroke="#000000" stroke-width="2"/>')
        _t(f, cx_, cy_ + 1, lab, 22, True, color="#ffffff")
    f.raw('</g>')
    n_none, n_arch, n_unesco = sum(1 for r in rows if r[0] is None), sum(1 for r in rows if r[4] and not r[5]), sum(1 for r in rows if r[5])
    n_beyond = sum(1 for r in rows if r[0] is not None and r[0] > AX)
    # ---- legend: the time bar. Above it the number of caves whose span includes the age, below it the MIS strip and the ka scale
    bx0, bx1 = 70, 1160
    BX = lambda a_: bx0 + (bx1 - bx0) * sq(a_)
    cy0 = Hm + 52                                   # top of the curve
    ch = 120
    grid = [i * 2.0 for i in range(int(AX / 2) + 1)]
    cover = [sum(1 for r in rows if r[0] is not None and r[1] <= a_ <= r[0]) for a_ in grid]
    cmax = max(cover)
    pts = " ".join(f"{BX(a_):.1f},{cy0 + ch - ch * n_ / cmax:.1f}" for a_, n_ in zip(grid, cover))
    f.raw(f'<polygon points="{bx0},{cy0 + ch} {pts} {bx1},{cy0 + ch}" fill="#cdd5d8" stroke="#7a8a92" stroke-width="1.5"/>')
    _t(f, bx0 - 12, cy0, str(cmax), 22, color=MUTED, anchor="end")
    _t(f, bx0 - 12, cy0 + ch, "0", 22, color=MUTED, anchor="end")
    sy = cy0 + ch + 8                               # MIS strip
    for st_ in sorted(stages):
        a0, a1 = stages.get(st_ - 1, 0.0), stages[st_]
        if a0 >= AX:
            continue
        x0_, x1_ = BX(a0), BX(min(a1, AX))
        f.rect(round(x0_, 1), sy, round(x1_ - x0_, 1), 34, "#fcd9c4" if st_ % 2 == 1 else "#d4e5f5", "#ffffff", 0, 1.5)
        if x1_ - x0_ >= 28:
            _t(f, (x0_ + x1_) / 2, sy + 17, str(st_), 22, True, color="#8b1a00" if st_ % 2 == 1 else "#003f6b")
    _t(f, bx0 - 12, sy + 17, "MIS", 22, color=MUTED, anchor="end")
    gy = sy + 42                                    # the colour bar
    n_seg = 200
    for i in range(n_seg):
        f.rect(round(bx0 + (bx1 - bx0) * i / n_seg, 2), gy, round((bx1 - bx0) / n_seg + 0.6, 2), 30, ramp((i + 0.5) / n_seg), None, 0, 0)
    f.rect(bx0, gy, bx1 - bx0, 30, "none", "#2b2b29", 0, 1.2)
    for a_ in (0, 10, 25, 50, 100, 200, 300, 400, 500, 600):
        f.line(round(BX(a_), 1), gy + 30, round(BX(a_), 1), gy + 38, None, w=1.2, color=MUTED)
        _t(f, BX(a_) - (12 if a_ == 600 else 0), gy + 62, "600+" if a_ == 600 else str(a_), 22, color=MUTED)
    _t(f, (bx0 + bx1) / 2, gy + 100, "ka BP", 22, color=MUTED)
    sx = 1250
    y = cy0 + 6
    n_arch_all = n_arch + n_unesco
    for kind, col, text in (("ring", "#9a3412", "archaeological use possible"), ("none", "#5f5e5a", "no dated sample")):
        if kind == "ring":
            f.raw(f'<circle cx="{sx + 14}" cy="{y}" r="12" fill="none" stroke="{col}" stroke-width="3.5"/>')
        else:
            f.raw(f'<circle cx="{sx + 14}" cy="{y}" r="8" fill="#ffffff" stroke="{col}" stroke-width="2"/>')
        _t(f, sx + 40, y, text, 22, color=MUTED, anchor="start", maxw=420)
        y += 50
    y += 20
    for lab, col, text in (("1", "#9a3412", "Spannagel Cave"), ("2", "#9a3412", "Piani Eterni karst system"), ("E", "#166534", "Eifel region")):
        f.raw(f'<circle cx="{sx + 20}" cy="{y}" r="19" fill="{col}" stroke="#000000" stroke-width="2"/>')
        _t(f, sx + 20, y + 1, lab, 22, True, color="#ffffff")
        _t(f, sx + 52, y, text, 22, color=MUTED, anchor="start", maxw=390)
        y += 50
    f.save()
    return {"caves": len(caves), "none": n_none, "beyond600": n_beyond, "arch": n_arch + n_unesco, "max_cover": cmax}


def _hav(a, b):
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


CROSSWALK_CLASSES = ("Cave", "ArchaeologicalCaveSite", "CIFindspot", "CIArchaeologicalSite", "DrillingSite", "IceCore",
                     "IceCoreObservation", "SpeleothemObservation", "AgeAssignment", "MISMembershipAssignment", "AgeModel",
                     "DataSource", "IceCoreDataset", "DatingMethod", "GrowthHiatus", "DrillingCampaign", "MarineIsotopeStage")


def crosswalk(D: AY.ArchData) -> dict:
    """Replacement for the OntDoc screenshots: the classes of the paper, each with the rdfs:subClassOf chain that carries it
    into the CIDOC CRM family, read from the ontology files. The pages themselves are linked from the text."""
    import model_data as md
    import model_figs as F
    M = md.Model()
    iris = ["http://w3id.org/geo-lod/" + c for c in CROSSWALK_CLASSES]
    rows = []
    for iri in iris:
        assert iri in M.classes, iri
        _, chain = M.anchors(iri)
        assert chain, f"{iri}: no CRM-family ancestor"
        mids = [n for n in chain[1:-1] if not md.ns_key(n)]
        rows.append((iri, chain[-1], mids))
    rows.sort(key=lambda r: (F.FAM_ORDER[md.family(r[1])], M.curie(r[1]), tuple(M.curie(m) for m in r[2]), M.curie(r[0])))
    Kc = max(len(r[2]) for r in rows)
    colw = [430] + [300] * Kc + [470]
    ncol = len(colw)
    gap = (1700 - 40 - math.fsum(colw)) / (ncol - 1)
    xs = [20 + math.fsum(colw[:i]) + gap * i for i in range(ncol)]
    bh, step = 42, 56
    y_left = {r[0]: 30 + i * step for i, r in enumerate(rows)}
    nodes = {}
    for iri, anchor, mids in rows:
        cy = y_left[iri] + bh / 2
        for j, m in enumerate(mids):
            nodes.setdefault((m, Kc - len(mids) + j + 1), []).append(cy)
        nodes.setdefault((anchor, ncol - 1), []).append(cy)
    pos = {}
    for col in range(1, ncol):
        last = -1e9
        for k in sorted((k for k in nodes if k[1] == col), key=lambda k: (sum(nodes[k]) / len(nodes[k]), M.curie(k[0]))):
            y = max(sum(nodes[k]) / len(nodes[k]) - bh / 2, last + bh + 10)
            pos[k] = y; last = y
    height = int(max(list(y_left.values()) + list(pos.values())) + bh + 110)
    f = Fig("paper-crosswalk", "The classes of the paper and the CIDOC CRM family classes that carry them", 1700, height, OUT)
    drawn = set()
    for iri, anchor, mids in rows:
        seq = [(iri, 0)] + [(m, Kc - len(mids) + j + 1) for j, m in enumerate(mids)] + [(anchor, ncol - 1)]
        for a, b in zip(seq, seq[1:]):
            if (a, b) in drawn:
                continue
            drawn.add((a, b))
            ya = (y_left[a[0]] if a[1] == 0 else pos[a]) + bh / 2
            yb = pos[b] + bh / 2
            x1, x2 = xs[a[1]] + colw[a[1]] + 2, xs[b[1]] - 2
            xm = (x1 + x2) / 2
            f.path(f"M {x1:.1f} {ya:.1f} C {xm:.1f} {ya:.1f} {xm:.1f} {yb:.1f} {x2:.1f} {yb:.1f}", "a")
    for iri, anchor, mids in rows:
        x, y, w = xs[0], y_left[iri], colw[0]
        f.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{bh}" rx="8" fill="{F.fill_of(iri)}" stroke="#000000" stroke-width="1.4"/>')
        _t(f, x + 14, y + bh / 2, M.classes[iri].local, 22, True, anchor="start", maxw=w - 28)
    for (iri, col), y in pos.items():
        f.raw(f'<rect x="{xs[col]:.1f}" y="{y:.1f}" width="{colw[col]}" height="{bh}" rx="8" fill="{F.fill_of(iri)}" stroke="#000000" stroke-width="1.4"/>')
        _t(f, xs[col] + colw[col] / 2, y + bh / 2, M.curie(iri), 22, True, maxw=colw[col] - 16)
    fams = []
    for fill, label in ((F.fill_of(iris[0]), "geolod:"), (F.FAM_FILL["crm"], "CIDOC CRM"), (F.FAM_FILL["sci"], "CRMsci"),
                        (F.FAM_FILL["arch"], "CRMarchaeo"), (F.FAM_FILL[None], "other vocabulary")):
        used = fill == F.fill_of(iris[0]) or any(F.fill_of(a) == fill for _, a, _ in rows) or any(F.fill_of(m) == fill for _, _, ms in rows for m in ms)
        if used:
            fams.append((fill, label))
    x = 20
    for fill, label in fams:
        f.rect(x, height - 56, 26, 26, fill, "#000000", 4, 1.2)
        _t(f, x + 38, height - 43, label, 22, color=MUTED, anchor="start")
        x += 38 + tw(label, 22) + 50
    f.save()
    return {"classes": len(rows), "anchors": sorted({M.curie(a) for _, a, _ in rows})}


def fig2(D: AY.ArchData) -> dict:
    """Fig. 2 for the paper, built like the repo plates: vertical age axis, MIS bands (odd warm, even cold, pale where the
    record does not reach), the measured values in grey behind a rolling median over 11 points, gaps shown as gaps.
    Part one, panels a to e: the five EPICA Dome C proxies, read from the committed graph. Part two, panels f to i: two
    SISAL caves, read from the pipeline CSVs of the sites (the committed graph holds no per-sample SISAL values)."""
    import csv
    import numpy as np
    sys.path.insert(0, str(D.repo / "ontology"))
    import geo_lod_figures as gf
    import cluster_measurement as MT
    import cluster_mis as MS
    from statistics import median
    M = MT.MeasData(D.repo)
    ep, G_, SOSA_ = M.epica, MT.G, MT.SOSA
    # the beginning of each stage: stage s runs from age[s-1] to age[s], age[0] = 0 (Railsback et al.)
    ages_mis = {}
    for st, _t_, _d, a in MS.MisData(D.repo).depths:
        ages_mis[st] = a
    stages = [(st, ages_mis.get(st - 1, 0.0), ages_mis[st]) for st in sorted(ages_mis)]
    WARM, COLD, WARM_L, COLD_L = "#fcd9c4", "#d4e5f5", "#8b1a00", "#003f6b"
    RAWC = "#b4b2aa"
    SCL = [1.35]                   # px per ka: the ice cores run to 810 ka, the two caves to 290 ka and get 3.0 px per ka, so that the speleothems can be read
    LEFT, RIGHT = 100, 1640
    EPI = (("ch4", "CH4, ppb", False), ("dd", "\u03b4D, \u2030", False), ("dust", "dust, \u00b5g/kg (log)", True),
           ("d18o", "\u03b418O of O2, \u2030", False), ("do2n2", "\u03b4O2/N2, \u2030", False))

    def profile(f, Xv, Ya, pts, breaks, colour, wd, ring=6):
        """As gf.draw_profile: solid between the breaks, dashed across each break, the break ends ringed in white."""
        starts = [0] + [after for _b, after in breaks]
        ends = [before for before, _a in breaks] + [len(pts) - 1]
        for i0, i1 in zip(starts, ends):
            seg = pts[i0:i1 + 1]
            if len(seg) > 1:
                d = " ".join(("M" if i == 0 else "L") + f"{Xv(r[1])} {Ya(r[0])}" for i, r in enumerate(seg))
                f.raw(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{wd}" stroke-linejoin="round"/>')
        for before, after in ([] if colour == RAWC else breaks):      # the grey raw values keep the gap but not the rings, so that the page stays readable
            f.raw(f'<path d="M{Xv(pts[before][1])} {Ya(pts[before][0])} L{Xv(pts[after][1])} {Ya(pts[after][0])}" fill="none" stroke="{colour}" stroke-width="{wd}" stroke-dasharray="9 6"/>')
        for i in sorted({i for pair in ([] if colour == RAWC else breaks) for i in pair}):
            f.raw(f'<circle cx="{Xv(pts[i][1])}" cy="{Ya(pts[i][0])}" r="{ring}" fill="#ffffff" stroke="{colour}" stroke-width="2"/>')

    def runs(pts, gapmin):
        out, cur = [], []
        for r in pts:
            if cur and r[0] - cur[-1][0] > gapmin:
                out.append(cur)
                cur = []
            cur.append(r)
        return out + ([cur] if cur else [])

    def nice_ticks(lo, hi, n=4):
        raw = (hi - lo) / n
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
        t = math.ceil(lo / step) * step
        out = []
        while t <= hi + 1e-9:
            out.append(round(t, 6))
            t += step
        return out

    def panel(f, x0, w, top, amax, pts, log, letter, name, layers):
        """One column: bands, raw values, the median per run. pts = [(age, raw)], meds = [[(age, median)] per run]."""
        vals = [r[1] for r in pts]
        lo, hi = min(vals), max(vals)
        if log:
            lo, hi = math.log10(max(lo, 1e-3)), math.log10(hi)
        pad = (hi - lo) * 0.04
        lo, hi = lo - pad, hi + pad
        Xv = lambda v: round(x0 + 6 + (w - 12) * ((math.log10(max(v, 1e-3)) if log else v) - lo) / (hi - lo), 1)
        Ya = lambda a: round(top + a * SCL[0], 1)
        f.rect(x0, 160 if False else top, w, round(amax * SCL[0], 1), "#ffffff")
        have = [r[0] for r in pts]
        for st, a0, a1 in stages:
            if a0 >= amax:
                continue
            a1c = min(a1, amax)
            warm = st % 2 == 1
            covered = any(a0 <= a < a1 for a in have)
            col = WARM if warm else COLD
            if covered:
                f.rect(x0, Ya(a0), w, round((a1c - a0) * SCL[0], 1), col)
            else:
                f.raw(f'<rect x="{x0}" y="{Ya(a0)}" width="{w}" height="{round((a1c - a0) * SCL[0], 1)}" fill="{col}" fill-opacity=".35" stroke="{WARM_L if warm else COLD_L}" stroke-width="1.2" stroke-dasharray="6 5"/>')
        ticks = [10 ** e for e in range(math.ceil(lo), math.floor(hi) + 1)] if log else nice_ticks(lo + pad, hi - pad)
        for v in ticks:
            f.line(Xv(v), top, Xv(v), top + amax * SCL[0], None, w=1, color="#ffffff")
            _t(f, Xv(v), top - 16, f"{v:g}", 22, color=MUTED)
        for lay_pts, lay_brk, lay_col, lay_w in layers:
            profile(f, Xv, Ya, lay_pts, lay_brk, lay_col, lay_w)
        f.rect(x0, top, w, round(amax * SCL[0], 1), "none", "#7a7a72", 0, 1.2)
        f.rect(x0, top - 108, 38, 38, "#000000", "#000000", 6, 1)
        _t(f, x0 + 19, top - 89, letter, 26, True, color="#ffffff")
        _t(f, x0 + 48, top - 89, name, 24, True, anchor="start", maxw=w - 52)

    def margins(f, top, amax, head_y):
        for a in range(0, int(amax) + 1, 100):
            f.line(LEFT - 8, round(top + a * SCL[0], 1), LEFT, round(top + a * SCL[0], 1), None, w=1.2, color=MUTED)
            _t(f, LEFT - 12, top + a * SCL[0], str(a), 22, color=MUTED, anchor="end")
        _t(f, LEFT - 12, head_y, "ka BP", 22, color=MUTED, anchor="end")
        _t(f, RIGHT + 32, head_y, "MIS", 22, color=MUTED)
        for st, a0, a1 in stages:
            if a0 >= amax:
                continue
            a1c = min(a1, amax)
            _t(f, RIGHT + 32, top + (a0 + a1c) / 2 * SCL[0], str(st), 22, True, color=WARM_L if st % 2 == 1 else COLD_L, maxw=44)

    # ------------------------------------------------------------ part one: EPICA
    series = {}
    for ds in ep.subjects(RDF.type, G_.IceCoreDataset):
        key = str(ds).rsplit("/", 1)[1].replace("dataset_", "")
        rows = []
        for o in ep.objects(ds, G_.hasObservation):
            v = [ep.value(o, G_[k]) for k in ("ageKaBP", "measuredValue", "smoothedValue_rollingMedian")]
            rows.append((float(v[0]), float(v[1]), float(v[2])))
        series[key] = sorted(rows)
    amax_a = 810.0
    ncol, gap = 5, 20
    w = (RIGHT - LEFT - gap * (ncol - 1)) / ncol
    top_a = 190
    top_b = top_a + round(amax_a * SCL[0]) + 290
    amax_b = 290.0
    cave_rows = {}
    for key in ("spannagel_all", "piani_eterni_karst_system"):
        with open(D.repo / "data/derived/sisal/sites" / f"{key}.csv", encoding="utf-8", newline="") as fh:
            cave_rows[key] = list(csv.DictReader(fh))
    H = top_b + round(amax_b * 3.0) + 120
    f = Fig("paper-fig2", "Pipeline outputs on a vertical age axis: EPICA Dome C and two SISAL caves", 1700, H, OUT)
    _t(f, LEFT, 50, "EPICA Dome C: five measured series on the timescales they are dated on", 26, True, anchor="start", maxw=1540)
    margins(f, top_a, amax_a, top_a - 16)
    info, nbreak = {}, {}
    for i, (key, name, log) in enumerate(EPI):
        pts = series[key]
        brk = gf.find_breaks(np.array([r[0] for r in pts]), 15.0)     # the repo threshold for the ice cores
        layers = [([(r[0], r[1]) for r in pts], brk, RAWC, 1.1), ([(r[0], r[2]) for r in pts], brk, "#000000", 2)]
        panel(f, LEFT + i * (w + gap), w, top_a, amax_a, [(r[0], r[1]) for r in pts], log, "abcde"[i], name, layers)
        nbreak[key] = len(brk)
        info[key] = len(pts)
    # ------------------------------------------------------------ part two: SISAL
    _t(f, LEFT, top_b - 205, "SISAL v3: two Alpine caves whose records reach MIS 7 and 6, \u03b418O and \u03b413C of every entity", 26, True, anchor="start", maxw=1540)
    SCL[0] = 3.0
    margins(f, top_b, amax_b, top_b - 16)
    wb = (RIGHT - LEFT - gap * 3) / 4
    names = {"spannagel_all": "Spannagel Cave", "piani_eterni_karst_system": "Piani Eterni karst system"}
    dropped = 0
    sisal_breaks = 0
    for ci, key in enumerate(("spannagel_all", "piani_eterni_karst_system")):
        by_ent = {}
        for r in cave_rows[key]:
            a = float(r["age_bp"]) / 1000.0
            if a < 0:
                dropped += 1
                continue
            by_ent.setdefault(r["entity_name"], []).append((a, r))
        order = sorted(by_ent, key=lambda e: -max(a for a, _r in by_ent[e]))      # the one reaching furthest back first, as the repo plates
        cols = gf.series_colours(len(order))
        for vi, (col, vname) in enumerate((("d18o", "\u03b418O, \u2030"), ("d13c", "\u03b413C, \u2030"))):
            allpts, raw_layers, med_layers = [], [], []
            for ent, colour in zip(order, cols):
                pts = sorted((a, float(r[col])) for a, r in by_ent[ent] if r[col] not in ("", "NULL"))
                if len(pts) < 2:
                    continue
                ages = np.array([p[0] for p in pts])
                vals = np.array([p[1] for p in pts])
                brk = gf.find_breaks_relative(ages)
                sm = gf.smooth_by_run(vals, brk, "median", 11)
                raw_layers.append((pts, brk, RAWC, 1.1))
                med_layers.append(([(a_, float(v_)) for a_, v_ in zip(ages, sm)], brk, colour, 2))
                allpts += pts
                sisal_breaks += len(brk) if vi == 0 else 0
            allpts.sort()
            x0 = LEFT + (ci * 2 + vi) * (wb + gap)
            panel(f, x0, wb, top_b, amax_b, allpts, False, "fghi"[ci * 2 + vi], vname, raw_layers + med_layers)
        _t(f, LEFT + ci * 2 * (wb + gap) + wb + gap / 2, top_b - 152, f"{names[key]}, {len(order)} entities", 24, True, maxw=2 * wb)
        lx0 = LEFT + ci * 2 * (wb + gap)
        lx, ly = lx0, top_b + round(amax_b * SCL[0]) + 32
        for ent, colour in zip(order, cols):
            need = 36 + tw(ent, 22) + 26
            if lx + need - 26 > lx0 + 2 * wb + gap:
                lx, ly = lx0, ly + 32
            f.line(lx, ly, lx + 28, ly, None, w=4, color=colour)
            _t(f, lx + 36, ly, ent, 22, color=MUTED, anchor="start")
            lx += need
    f.save()
    return {"epica": info, "epica_breaks": nbreak, "sisal_breaks_d18o": sisal_breaks, "dropped_negative_ages": dropped}


def taxonomy(D: AY.ArchData) -> dict:
    """Fig. 3: class hierarchy of the geo-lod ontology (core, EPICA, SISAL; the CI classes sit in the core file) as a tree from
    left to right: CRM-family and other vocabulary classes at the roots, geo-lod classes solid, ancestors outside geo-lod dashed,
    a second parent as a dashed line. A coloured stripe on the left of a box names the domain extension. Read from the
    ontology files by model_data; nothing here names a class."""
    import model_data as md
    import model_figs as MF
    from collections import defaultdict
    M = md.Model()
    own = [c for c in M.classes_of("core", "epica", "sisal") if md.ns_key(c.iri) == "geolod"]
    ownset = {c.iri for c in own}
    dom = {}
    for c in own:
        dom[c.iri] = "ci" if c.local.startswith("CI") else ("epica" if c.primary == "epica" else "sisal" if c.primary == "sisal" else None)
    STRIPE = {"epica": "#2b6cb0", "sisal": "#2f855a", "ci": "#c05621"}
    label_of = {c.iri: c.local for c in own}
    # CRM-family classes carry their family in the fill colour (legend), so the prefix is left off; other vocabularies keep theirs
    lab = lambda i: label_of.get(i) or (M.curie(i).split(":", 1)[1] if md.family(i) else M.curie(i))
    import crm_tree as CT

    def primary(iri):
        ps = M.parents(iri)
        if iri not in ownset and md.family(iri) in ("sci", "arch", "geo") and iri in CT.PARENT:
            q_ = CT.PARENT[iri]            # an extension class hangs below the first CIDOC CRM core class it specialises
            while q_ in CT.PARENT and not q_.startswith(CT.CRM):
                q_ = CT.PARENT[q_]
            return q_
        if not ps or (md.family(iri) and iri not in ownset):
            return None
        inside = [q for q in ps if q in ownset]
        fam = [q for q in ps if md.family(q)]
        return (inside or fam or ps)[0]

    parent = {}

    def chain(iri):
        while iri not in parent:
            q = primary(iri)
            parent[iri] = q
            if q is None:
                break
            iri = q

    for c in own:
        chain(c.iri)
    extras = []
    for c in own:
        for q in M.parents(c.iri):
            if q != parent[c.iri]:
                extras.append((c.iri, q))
                chain(q)
    children = defaultdict(list)
    for n_, q in parent.items():
        if q:
            children[q].append(n_)
    for q in children:
        children[q].sort(key=M.curie)
    roots = sorted((n_ for n_, q in parent.items() if q is None), key=lambda n_: (MF.FAM_ORDER[md.family(n_)], M.curie(n_)))
    depth = {}

    def dep(n_):
        if n_ not in depth:
            depth[n_] = 0 if parent[n_] is None else dep(parent[n_]) + 1
        return depth[n_]

    for n_ in parent:
        dep(n_)
    SZ = MIN_TYPE
    ncol = max(depth.values()) + 1
    # the leaves of the deepest column stand below their parent, indented, instead of in a column of their own
    nested = {n_ for n_ in parent if depth[n_] == ncol - 1 and ncol > 2}
    cdep = {n_: depth[n_] - 1 if n_ in nested else depth[n_] for n_ in parent}
    ncol = max(cdep.values()) + 1
    INDENT = 34
    need = lambda n_: tw(lab(n_), SZ, True) + (24 if dom.get(n_) else 10) + (INDENT if n_ in nested else 0)
    colw = [max(need(n_) for n_ in parent if cdep[n_] == d) for d in range(ncol)]
    GAP = (W - 32 - math.fsum(colw)) / max(ncol - 1, 1)
    print("taxonomy: columns", [round(c) for c in colw], "gap", round(GAP), "nested", len(nested))
    assert GAP >= 28, f"taxonomy: {ncol} columns leave {GAP:.0f} px between them"
    xcol = [16 + math.fsum(colw[:d]) + GAP * d for d in range(ncol)]
    xn = {n_: xcol[cdep[n_]] + (INDENT if n_ in nested else 0) for n_ in parent}
    wd = {n_: colw[cdep[n_]] - (INDENT if n_ in nested else 0) for n_ in parent}
    ypos, cur = {}, [0]

    def place(n_):
        ch = children.get(n_, [])
        if not ch:
            ypos[n_] = cur[0]
            cur[0] += 1
            return
        if any(c_ in nested for c_ in ch):          # the parent takes a row, its nested leaves follow below it
            ypos[n_] = cur[0]
            cur[0] += 1
            for c_ in ch:
                ypos[c_] = cur[0]
                cur[0] += 1
            return
        for c_ in ch:
            place(c_)
        ypos[n_] = (ypos[ch[0]] + ypos[ch[-1]]) / 2

    for r_ in roots:
        place(r_)
    rowh, top, bh = 52, 30, 40
    H_ = int(top + cur[0] * rowh + 250)
    f = Fig("paper-taxonomy", "Class hierarchy of the geo-lod ontology with its domain extensions and the vocabularies it reaches", W, H_, OUT)
    cy = {n_: top + ypos[n_] * rowh + bh / 2 for n_ in parent}
    for n_, q in parent.items():
        if q and n_ in nested:
            vx = xn[q] + 16
            f.path(f"M {xn[n_]:.1f} {cy[n_]:.1f} L {vx:.1f} {cy[n_]:.1f} L {vx:.1f} {cy[q] + bh / 2 + 2:.1f}", "t")
        elif q:
            mx = xn[n_] - GAP / 2
            f.path(f"M {xn[n_]:.1f} {cy[n_]:.1f} L {mx:.1f} {cy[n_]:.1f} L {mx:.1f} {cy[q]:.1f} L {xn[q] + wd[q] + 2:.1f} {cy[q]:.1f}", "t")
    for n_, q in extras:
        mx = xn[n_] - GAP / 2 + 14 - (INDENT if n_ in nested else 0)
        f.path(f"M {xn[n_]:.1f} {cy[n_] + 7:.1f} L {mx:.1f} {cy[n_] + 7:.1f} L {mx:.1f} {cy[q]:.1f} L {xn[q] + wd[q] + 2:.1f} {cy[q]:.1f}", "t", True)
    for n_ in parent:
        x_, w_ = xn[n_], wd[n_]
        d_ = bool(md.ns_key(n_)) and n_ not in ownset
        ds = ' stroke-dasharray="7 5" stroke-width="1.8"' if d_ else ' stroke-width="1.2"'
        f.raw(f'<rect x="{x_:.1f}" y="{cy[n_] - bh / 2:.1f}" width="{w_:.1f}" height="{bh}" rx="8" fill="{MF.fill_of(n_)}" stroke="#000000"{ds}/>')
        if dom.get(n_):
            f.raw(f'<path d="M {x_ + 8:.1f} {cy[n_] - bh / 2 + 1:.1f} L {x_ + 9:.1f} {cy[n_] - bh / 2 + 1:.1f} L {x_ + 9:.1f} {cy[n_] + bh / 2 - 1:.1f} L {x_ + 8:.1f} {cy[n_] + bh / 2 - 1:.1f} Z" fill="none"/>'
                  f'<rect x="{x_ + 1:.1f}" y="{cy[n_] - bh / 2 + 1:.1f}" width="12" height="{bh - 2}" rx="5" fill="{STRIPE[dom[n_]]}"/>')
        _t(f, x_ + w_ / 2 + (6 if dom.get(n_) else 0), cy[n_] + 1, lab(n_), SZ, True)
    items = [(MF.OWN_FILL["geolod"], "geolod class")] + MF.family_items(parent)
    ph = 196
    py = f.h - ph - 18
    f.rect(16, py, W - 32, ph, "#f6f6f3", "#c9c7bf", 12, 1.2)

    def sample(x_, y_, text, fill, stripe=None):
        w_ = tw(text, SZ, True) + (46 if stripe else 28)
        f.raw(f'<rect x="{x_:.1f}" y="{y_}" width="{w_:.1f}" height="40" rx="8" fill="{fill}" stroke="#000000" stroke-width="1.2"/>')
        if stripe:
            f.raw(f'<rect x="{x_ + 1:.1f}" y="{y_ + 1}" width="12" height="38" rx="5" fill="{stripe}"/>')
        _t(f, x_ + w_ / 2 + (7 if stripe else 0), y_ + 21, text, SZ, True)
        return x_ + w_ + 22

    LX = 330                                                    # where the samples start, right of the row labels
    for i, lab_ in enumerate(("Meta ontologies", "Instance level", "Edges")):
        _t(f, 36, py + 36 + i * 56, lab_, SZ, True, color=MUTED, anchor="start")
    x_ = LX
    for fill, txt in items:
        x_ = sample(x_, py + 16, txt, fill)
    x_ = LX
    for k_, txt in (("epica", "EPICA"), ("sisal", "SISAL"), ("ci", "Campanian Ignimbrite")):
        x_ = sample(x_, py + 72, txt, MF.OWN_FILL["geolod"], STRIPE[k_])
    x_ = LX
    for dashed, txt in ((False, "subclass of"), (True, "second parent")):
        f.path(f"M {x_:.1f} {py + 148} L {x_ + 90:.1f} {py + 148}", "t", dashed)
        _t(f, x_ + 108, py + 148, txt, SZ, color=MUTED, anchor="start")
        x_ += 108 + tw(txt, SZ) + 50
    f.save()
    return {"geolod": len(own), "nodes": len(parent), "rows": cur[0], "columns": ncol, "height": H_}


def coin(D: AY.ArchData) -> dict:
    """Fig. 1: the FAIR4RS coin. One coin with two halves, executable reproducibility (left) and semantic interoperability
    (right), the RSE methodology in the middle; a squirrel (Research Squirrel Engineers) sits on the coin. Data go in on the left, the
    results come out on both sides. Replaces the generated infographic and keeps its content."""
    W_, H = 1700, 1638
    f = Fig("paper-coin", "The FAIR4RS coin: executable reproducibility and semantic interoperability as the two faces of one RSE methodology", W_, H, OUT)
    cx, cy_, r = 850, 896, 540
    A_FILL, B_FILL, RIM = "#d4e3f5", "#d9ecc8", "#e8d49a"
    ACC_A, ACC_B = "#1f4e79", "#2f6b2f"
    # the squirrel (Research Squirrel Engineers) sits behind the top of the coin; the coin covers its feet. Outline only, one
    # half drawn mirrored: blue left, green right, so both halves carry a bushy tail, an ear, an eye and a paw.
    hy, k = cy_ - r + 14, 1.4
    P = lambda x_, y_: f"{cx + x_ * k:.1f} {hy + y_ * k:.1f}"
    parts, fills = [], []
    for sg in (-1, 1):
        S = lambda x_, y_, sg=sg: P(sg * x_, y_)
        parts += [
            f"M {S(0, -214)} C {S(34, -214)} {S(58, -198)} {S(58, -172)} C {S(58, -148)} {S(32, -132)} {S(0, -132)}",          # head
            f"M {S(26, -206)} C {S(26, -232)} {S(36, -248)} {S(48, -254)} C {S(58, -236)} {S(62, -212)} {S(54, -192)}",         # ear
            f"M {S(40, -240)} C {S(42, -228)} {S(44, -220)} {S(48, -214)}",                                                      # ear tuft
            f"M {S(36, -152)} L {S(66, -160)} M {S(36, -144)} L {S(68, -142)}",                                                  # whiskers
            f"M {S(0, -134)} C {S(6, -124)} {S(15, -124)} {S(20, -131)}",                                                        # smile
            f"M {S(22, -128)} C {S(62, -120)} {S(80, -70)} {S(72, -8)} L {S(70, 26)}",                                           # back and flank
            f"M {S(0, -112)} C {S(30, -106)} {S(44, -64)} {S(36, -12)}",                                                         # belly line
            f"M {S(24, -104)} C {S(42, -92)} {S(38, -64)} {S(20, -60)}",                                                         # arm
            f"M {S(72, -8)} C {S(156, 12)} {S(196, -78)} {S(164, -150)} C {S(144, -194)} {S(150, -226)} {S(124, -250)} "
            f"C {S(102, -244)} {S(90, -212)} {S(96, -170)} C {S(100, -130)} {S(96, -90)} {S(78, -52)}",                          # tail
            f"M {S(152, -46)} C {S(170, -90)} {S(152, -126)} {S(140, -166)} M {S(124, -34)} C {S(136, -70)} {S(124, -100)} {S(118, -128)}",  # fur strokes
        ]
    parts += [
        f"M {P(-17, -86)} C {P(-19, -102)} {P(19, -102)} {P(17, -86)} Z",                                                     # acorn cap
        f"M {P(-14, -86)} C {P(-15, -54)} {P(15, -54)} {P(14, -86)} Z M {P(0, -54)} L {P(0, -48)}",                           # acorn nut and tip
    ]
    dots = [(26, -174, 7, 1), (-26, -174, 7, 1), (0, -148, 8, 1)]
    f.raw(f'<defs><clipPath id="sqL"><rect x="0" y="-20" width="{cx}" height="{H}"/></clipPath><clipPath id="sqR"><rect x="{cx}" y="-20" width="{W_ - cx}" height="{H}"/></clipPath></defs>')
    for cid, col in (("sqL", ACC_A), ("sqR", ACC_B)):
        f.raw(f'<g clip-path="url(#{cid})" fill="none" stroke="{col}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
              + "".join(f'<path d="{d}"/>' for d in parts)
              + "".join(f'<circle cx="{cx + x_ * k:.1f}" cy="{hy + y_ * k:.1f}" r="{r_}" fill="{col}" stroke="none"/>' for x_, y_, r_, _ in dots)
              + "".join(f'<circle cx="{cx + x_ * k + 2.5:.1f}" cy="{hy + y_ * k - 2.5:.1f}" r="2.2" fill="#ffffff" stroke="none"/>' for x_, y_, r_, _ in dots[:2])
              + '</g>')
    # the coin: a darker disc below suggests its thickness, then the rim with beads and the two halves
    f.raw(f'<circle cx="{cx}" cy="{cy_ + 18}" r="{r}" fill="#b89a52" stroke="#000000" stroke-width="3"/>')
    f.raw(f'<circle cx="{cx}" cy="{cy_}" r="{r}" fill="{RIM}" stroke="#000000" stroke-width="3.5"/>')
    f.raw(f'<circle cx="{cx}" cy="{cy_}" r="{r - 20}" fill="none" stroke="#b89a52" stroke-width="9" stroke-dasharray="1 17" stroke-linecap="round"/>')
    ri = r - 44
    f.raw(f'<path d="M {cx} {cy_ - ri} A {ri} {ri} 0 0 0 {cx} {cy_ + ri} Z" fill="{A_FILL}" stroke="#000000" stroke-width="2.4"/>')
    f.raw(f'<path d="M {cx} {cy_ - ri} A {ri} {ri} 0 0 1 {cx} {cy_ + ri} Z" fill="{B_FILL}" stroke="#000000" stroke-width="2.4"/>')
    rc = 146
    faces = ((cx - 232, "Executable", "Reproducibility", ACC_A,
              ("Explicit Parameters", "Script-based Pipelines", "Version Control (Git)", "Modular Architecture", "Re-executable Notebooks"),
              "the repeatable run"),
             (cx + 232, "Semantic", "Interoperability", ACC_B,
              ("RDF Transformation", "Persistent Identifiers (PID)", "Shared Vocabularies", "Geo-referenced Entities", "Cross-domain Linking"),
              "the resolvable identifier"))
    for mx, l1, l2, acc, items, trust in faces:
        left = mx < cx
        px0 = cx - rc - 12 - 284 if left else cx + rc + 12
        _t(f, mx, cy_ - 322, l1, 38, True, color=acc)
        _t(f, mx, cy_ - 278, l2, 38, True, color=acc)
        f.line(mx - 160, cy_ - 245, mx + 160, cy_ - 245, None, w=2.6, color=acc)
        for i, t in enumerate(items):
            y_ = cy_ - 205 + i * 70
            f.rect(px0, y_, 284, 58, "#ffffff", "#000000", 12, 1.2)
            _t(f, px0 + 142, y_ + 29, t, 22, maxw=272)
        f.rect(mx - 168, cy_ + 175, 336, 112, acc, "#000000", 18, 1.6)
        _t(f, mx, cy_ + 205, "Unit of trust", 24, color="#ffffff")
        _t(f, mx, cy_ + 252, trust, 28, True, color="#ffffff", maxw=316)
    # the centre: RSE methodology, on both halves
    f.raw(f'<defs><clipPath id="med"><circle cx="{cx}" cy="{cy_ - 30}" r="{rc}"/></clipPath></defs>')
    f.raw(f'<circle cx="{cx}" cy="{cy_ - 30}" r="{rc}" fill="#ffffff" stroke="#000000" stroke-width="3"/>')
    f.raw(f'<rect x="{cx - rc}" y="{cy_ - 30 - rc}" width="{2 * rc}" height="{rc - 36}" fill="#3f444b" clip-path="url(#med)"/>')
    mc = cy_ - 30
    _t(f, cx, mc - 96, "RSE", 28, True, color="#ffffff")
    _t(f, cx, mc - 64, "Methodology", 28, True, color="#ffffff", maxw=2 * math.sqrt(rc * rc - 64 * 64) - 8)
    for dy, t, b in ((-16, "Software Engineering", False), (18, "FAIR4RS Principles", True), (52, "Sustainable", False), (82, "Research Software", False)):
        _t(f, cx, mc + dy, t, 24 if b else 22, b, maxw=2 * math.sqrt(rc * rc - dy * dy) - 8)
    # below the coin, head down: an acorn with a sprout, the seed the squirrel holds above, now growing (re-use)
    ay = cy_ + r + 6                                              # the tip disappears behind the FAIR4RS badge
    Q = lambda x_, y_: f"{cx + x_:.1f} {ay + y_:.1f}"
    acorn = [
        f"M {Q(0, 4)} C {Q(-26, 18)} {Q(-36, 44)} {Q(-34, 78)} L {Q(34, 78)} C {Q(36, 44)} {Q(26, 18)} {Q(0, 4)} Z",
        f"M {Q(-42, 78)} L {Q(42, 78)} C {Q(44, 102)} {Q(22, 114)} {Q(0, 114)} C {Q(-22, 114)} {Q(-44, 102)} {Q(-42, 78)} Z",
        f"M {Q(0, 114)} L {Q(0, 146)}",
        f"M {Q(0, 146)} C {Q(-10, 136)} {Q(-46, 138)} {Q(-58, 160)} C {Q(-34, 170)} {Q(-8, 166)} {Q(0, 146)} Z",
        f"M {Q(0, 146)} C {Q(10, 136)} {Q(46, 138)} {Q(58, 160)} C {Q(34, 170)} {Q(8, 166)} {Q(0, 146)} Z",
    ]
    for cid, col in (("sqL", ACC_A), ("sqR", ACC_B)):
        f.raw(f'<g clip-path="url(#{cid})" fill="none" stroke="{col}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
              + "".join(f'<path d="{d}"/>' for d in acorn) + '</g>')
    # the inscriptions on the rim: FAIR on top, FAIR4RS below
    f.rect(cx - 88, cy_ - r - 4, 176, 62, "#ffffff", "#000000", 31, 2.6)
    _t(f, cx, cy_ - r + 27, "FAIR", 42, True)
    f.rect(cx - 150, cy_ + r - 42, 300, 80, "#ffffff", "#000000", 40, 3)
    _t(f, cx, cy_ + r - 2, "FAIR4RS", 50, True)
    # in and out
    def db(x, y):
        f.raw(f'<path d="M {x - 34} {y - 30} v 60 a 34 12 0 0 0 68 0 v -60" fill="#ffffff" stroke="#000000" stroke-width="2.4"/>'
              f'<ellipse cx="{x}" cy="{y - 30}" rx="34" ry="12" fill="#ffffff" stroke="#000000" stroke-width="2.4"/>'
              f'<path d="M {x - 34} {y} a 34 12 0 0 0 68 0" fill="none" stroke="#000000" stroke-width="2"/>')

    def chart(x, y):
        f.raw(f'<rect x="{x - 56}" y="{y - 40}" width="112" height="80" fill="#ffffff" stroke="#000000" stroke-width="2.4"/>'
              f'<polyline points="{x - 46},{y + 26} {x - 28},{y - 4} {x - 10},{y + 12} {x + 8},{y - 26} {x + 26},{y + 6} {x + 46},{y - 14}" fill="none" stroke="{ACC_A}" stroke-width="4" stroke-linejoin="round"/>')

    def tag(x, y):
        f.raw(f'<path d="M {x - 48} {y - 6} L {x - 8} {y - 46} L {x + 46} {y - 46} L {x + 46} {y + 14} L {x + 6} {y + 54} Z" fill="#fbbf24" stroke="#000000" stroke-width="2.6" stroke-linejoin="round"/>'
              f'<circle cx="{x + 22}" cy="{y - 22}" r="7" fill="#ffffff" stroke="#000000" stroke-width="2.2"/>')

    def net(x, y, extra):
        pts = [(x, y), (x - 40, y - 28), (x + 40, y - 30), (x - 38, y + 30), (x + 42, y + 28)] + ([(x, y - 52), (x, y + 54)] if extra else [])
        for a_, b_ in pts[1:5]:
            f.raw(f'<line x1="{x}" y1="{y}" x2="{a_}" y2="{b_}" stroke="#000000" stroke-width="2.2"/>')
        for i, (a_, b_) in enumerate(pts):
            f.raw(f'<circle cx="{a_}" cy="{b_}" r="{11 if i == 0 else 8}" fill="{"#fbbf24" if i == 0 else "#ffffff"}" stroke="#000000" stroke-width="2.2"/>')

    def lens(x, y):
        f.raw(f'<circle cx="{x - 8}" cy="{y - 8}" r="26" fill="#ffffff" stroke="#000000" stroke-width="3.4"/>'
              f'<line x1="{x + 11}" y1="{y + 11}" x2="{x + 38}" y2="{y + 38}" stroke="#000000" stroke-width="7" stroke-linecap="round"/>')

    edge = lambda y_: math.sqrt(r * r - (y_ - cy_) ** 2)
    ys = (cy_ - 300, cy_ - 0, cy_ + 300)
    lefts = ((db, "Data Input", None, True), (chart, "Processing &", "Visualisation", False), (tag, "Tagged Release", "with DOI", False))
    rights = ((lambda x, y: net(x, y, False), "RDF /", "Linked Data"), (lambda x, y: net(x, y, True), "Knowledge", "Graph"), (lens, "Interdisciplinary", "Queries"))
    SZ_, LX_, RX_ = 32, 172, 1528
    # every icon is centred on its arrow; the shapes are not symmetric around their origin, so each gets an offset
    OFF = {db: (0, 0), chart: (0, 0), tag: (-1, -4), lens: (-3, -4)}
    for col, items in ((LX_, lefts), (RX_, rights)):
        for y_, it in zip(ys, items):
            icon, a_, b_ = it[0], it[1], it[2]
            ya = y_ - 38
            ox, oy = OFF.get(icon, (0, 0))
            icon(col + ox, ya + oy)
            _t(f, col, ya + 84, a_, SZ_, True)
            if b_:
                _t(f, col, ya + 84 + 40, b_, SZ_, True)
            if col == LX_:
                if it[3]:
                    f.line(col + 70, ya, cx - edge(ya) - 3, ya, "a")
                else:
                    f.line(cx - edge(ya) - 3, ya, col + 70, ya, "a")
            else:
                f.line(cx + edge(ya) + 3, ya, col - 70, ya, "a")
    f.save()
    return {}


FIGURES = {"coin": coin, "taxonomy": taxonomy, "fig2": fig2, "sisal_map": sisal_map, "epica_series": epica_series, "mis_depths": mis_depths, "crosswalk": crosswalk, "ci_map": ci_map, "eruption": eruption, "workflow": workflow, "crm_family": crm_family, "linked_graph": linked_graph, "epica_instance": epica_instance, "sisal_instance": sisal_instance}


def main(argv: list[str]) -> int:
    D = AY.ArchData()
    for name in (argv or FIGURES):
        print(f"  {name}: {FIGURES[name](D)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
