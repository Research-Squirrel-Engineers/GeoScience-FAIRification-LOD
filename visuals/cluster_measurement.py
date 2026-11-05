"""Figures of the cluster page "Observation and measurement".

The data come from the committed EPICA graph (`EPICA/rdf/epica_dome_c.ttl`: 4 904 ice core observations in five datasets,
each with its measured value, two smoothed values and the nodes the observation points to) and from the three ontology
files that define the classes. The SISAL speleothem observations belong to the large graph the pipeline writes; they are
not in the committed Turtle, and the page says so. Every number printed on a figure is counted from the graph; nothing
is typed in.

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import math
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

import model_data as md
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
G = Namespace("http://w3id.org/geo-lod/")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
PROV = Namespace("http://www.w3.org/ns/prov#")
EPICA = Namespace("http://w3id.org/geo-lod/epica/")
BLACK, GRID, INK = "#000000", "#d8d6ce", "#1f1f1d"
RAW_COLOUR, MEDIAN_COLOUR, SAVGOL_COLOUR = "#8a8a85", "#E69F00", "#0072B2"      # Okabe-Ito for the two filters
SERIES_KEY = "ch4"                                                              # the record drawn in the series figure
EXAMPLE = EPICA["obs_ch4_0001"]                                                 # the observation drawn in the pattern figure
VALUE_KINDS = [("measuredValue", "measured value"), ("standardDeviation", "standard deviation"),
               ("smoothedValue_rollingMedian", "rolling median"), ("smoothedValue_savgol", "Savitzky-Golay")]


class MeasData:
    """The EPICA graph and the ontology files in one graph `g` for the queries; the series and counts are read once."""

    def __init__(self, repo: Path = REPO):
        epica = Graph().parse(repo / "EPICA/rdf/epica_dome_c.ttl", format="turtle")
        g = Graph()
        trs = Graph().parse(repo / "ontology/trs.ttl", format="turtle")      # the timescales, so that their class can be shown
        for t in trs:
            epica.add(t)
        for t in epica:
            g.add(t)
        for rel in ("ontology/geo_lod_core.ttl", "EPICA/rdf/epica_ontology.ttl", "SISAL/rdf/sisal_ontology.ttl"):
            for t in Graph().parse(repo / rel, format="turtle"):
                g.add(t)
        for pfx, ns in (("geolod", G), ("sosa", SOSA), ("crm", CRM), ("qudt", QUDT), ("prov", PROV), ("epica", EPICA), ("rdfs", RDFS), ("dct", DCTERMS)):
            g.bind(pfx, ns)
        self.g, self.epica, self.repo = g, epica, repo
        prop = EPICA[f"property_{SERIES_KEY}"]
        rows = []
        for o in epica.subjects(SOSA.observedProperty, prop):
            vals = [epica.value(o, G[k]) for k in ("ageKaBP", "measuredValue", "smoothedValue_rollingMedian", "smoothedValue_savgol")]
            if any(v is None for v in vals):
                raise ValueError(f"{o} lacks one of age, measured value and the two smoothed values")
            rows.append((float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]), str(o).rsplit("/", 1)[1]))
        self.series = sorted(rows)
        self.property = prop
        # per dataset: title, unit, observations and how many carry each kind of value
        self.datasets: list[dict] = []
        for ds in sorted(epica.subjects(RDF.type, G.IceCoreDataset)):
            obs = sorted(epica.objects(ds, G.hasObservation))
            units = {str(u) for o in obs for u in epica.objects(o, QUDT.unit)}
            if len(units) != 1:
                raise ValueError(f"{ds}: the observations of a dataset should share one unit, found {sorted(units)}")
            counts = {k: sum(1 for o in obs if (o, G[k], None) in epica) for k, _ in VALUE_KINDS}
            title = str(next(epica.objects(ds, DCTERMS.title))).replace("EPICA Dome C - ", "")
            self.datasets.append({"key": str(ds).rsplit("/", 1)[1], "title": title, "unit": "unit:" + units.pop().rsplit("/", 1)[1],
                                  "n": len(obs), "counts": counts})
        self.datasets.sort(key=lambda d: (-d["n"], d["key"]))
        if not self.series or not self.datasets:
            raise ValueError("the committed EPICA graph holds no observations; the figures have nothing to draw")


def _node_class(g: Graph, node, nm) -> str:
    """The class a node is typed with for display: a geolod class if there is one, else any other, owl:NamedIndividual never."""
    types = sorted((t for t in g.objects(node, RDF.type) if t != OWL.NamedIndividual), key=str)
    types.sort(key=lambda t: not str(t).startswith(str(G)))
    return types[0].n3(nm) if types else ""


# ------------------------------------------------------------------ one observation, three views

def pattern_fig(M: md.Model, D: MeasData, outdir: Path, name: str) -> tuple[Fig, dict]:
    g = D.epica
    nm = g.namespace_manager
    cur = lambda t: t.n3(nm)
    obs = EXAMPLE
    if (obs, RDF.type, G.IceCoreObservation) not in g:
        raise ValueError(f"{name}: {obs} is not a geolod:IceCoreObservation in the committed graph")

    def one(pred: URIRef):
        v = g.value(obs, pred)
        if v is None:
            raise ValueError(f"{name}: {obs} has no {pred}")
        return v

    def number(v) -> str:
        return format(float(v), "g")

    def row(pred, kind, suffix=""):
        v = one(pred)
        if kind == "node":
            extra = ""
            if (v, G.windowSize, None) in g:
                extra = f" · window {number(g.value(v, G.windowSize))}" + (f", order {number(g.value(v, G.polyOrder))}" if (v, G.polyOrder, None) in g else "")
            return (cur(pred), "node", cur(v), _node_class(g, v, nm) + extra)
        if isinstance(v, Literal):
            return (cur(pred), "lit", number(v) + suffix, "")
        return (cur(pred), "lit", cur(v), "")

    panels = [
        ("SOSA: what was observed", "the observation as a sosa:Observation", [
            row(SOSA.observedProperty, "node"), row(SOSA.hasFeatureOfInterest, "node"),
            row(SOSA.hasSimpleResult, "lit"), row(SOSA.resultTime, "lit")]),
        ("CRM and PROV: where, from where, how", "the observation as a crmsci:S4_Observation", [
            row(CRM.P7_took_place_at, "node"), row(PROV.wasDerivedFrom, "node"), row(G.measurementType, "node"),
            row(G.ageChronology, "node"), row(G.atDepth_m, "lit", " m"), row(G.ageKaBP, "lit", " ka BP")]),
        ("geo-lod: the value and what was done to it", "the values stay on the observation; the filters are nodes", [
            row(QUDT.unit, "lit"), row(G.measuredValue, "lit"), row(G.standardDeviation, "lit"),
            row(G.smoothedValue_rollingMedian, "lit"), row(G.smoothingMethod_rollingMedian, "node"),
            row(G.smoothedValue_savgol, "lit"), row(G.smoothingMethod_savgol, "node")]),
    ]
    shown = {r[0] for _, _, rows in panels for r in rows}
    stmts = sorted((p for p in set(g.predicates(obs, None))), key=str)
    left_out = [cur(p) for p in stmts if cur(p) not in shown and p != RDF.type]
    n_shown = len(shown)

    W = 1900
    pw, gap, px0 = 590, 30, 50
    rh_lit, rh_node = 42, 86
    head = 96
    height = lambda rows: head + sum(rh_node if r[1] == "node" else rh_lit for r in rows) + 18
    ph = max(height(rows) for _, _, rows in panels)
    py = 330
    H = py + ph + 130
    f = Fig(name, "One observation in three views", W, H, outdir)
    f.text(50, 40, "One data point, three views: SOSA, CRM with PROV, and the values geo-lod adds", 26, True, anchor="start")
    f.text(50, 76, f"{cur(obs)}, a node of EPICA/rdf/epica_dome_c.ttl, with every statement read from the graph.", 19, color=MUTED, anchor="start")
    gl = F.OWN_FILL["geolod"]

    # the observation node, with its class chain
    chain = M.curie(str(G.IceCoreObservation))
    sup = M.parents(str(G.IceCoreObservation))
    sup2 = sorted({M.curie(q) for p in sup for q in M.parents(p)})
    cw, cx = 760, (W - 760) / 2
    f.raw(f'<rect x="{cx}" y="118" width="{cw}" height="104" rx="9" fill="{gl}" stroke="{BLACK}" stroke-width="1.4"/>')
    f.text(cx + cw / 2, 118 + 26, cur(obs), 22, True, BLACK, maxw=cw - 16)
    f.text(cx + cw / 2, 118 + 56, f"{chain}  →  " + ", ".join(M.curie(p) for p in sup), 16, color="#3a3935", maxw=cw - 16)
    f.text(cx + cw / 2, 118 + 80, "→  " + ", ".join(sup2) + "   (rdfs:subClassOf)", 16, color="#3a3935", maxw=cw - 16)

    for i, (title, sub, rows) in enumerate(panels):
        x = px0 + i * (pw + gap)
        mid = x + pw / 2
        f.path(f"M{W / 2} 222 L{W / 2} 262 L{mid} 262 L{mid} {py - 4}", "a")
        f.rect(x, py, pw, ph, "#fbfbf9", "#bdbbb2", 10, 1.2)
        f.text(x + 18, py + 30, title, 21, True, anchor="start", maxw=pw - 30)
        f.text(x + 18, py + 62, sub, 16, color=MUTED, anchor="start", maxw=pw - 30)
        y = py + head
        for pred, kind, val, cls in rows:
            if kind == "node":
                f.text(x + 18, y + 14, pred, 16, color=MUTED, anchor="start", maxw=pw - 40)
                bx, bw_ = x + 18, pw - 36
                f.raw(f'<rect x="{bx}" y="{y + 30}" width="{bw_}" height="{rh_node - 38}" rx="7" fill="{gl}" stroke="{BLACK}" stroke-width="1.1"/>')
                f.text(bx + bw_ / 2, y + 30 + 14, F.fit(val, 17, bw_ - 16, True), 17, True, BLACK, maxw=bw_ - 8)
                f.text(bx + bw_ / 2, y + 30 + 33, F.fit(cls, 14, bw_ - 16), 14, color="#3a3935", maxw=bw_ - 8)
                y += rh_node
            else:
                f.text(x + 18, y + rh_lit / 2, pred, 16, color=MUTED, anchor="start", maxw=pw - 190)
                f.text(x + pw - 18, y + rh_lit / 2, val, 19, color=INK, anchor="end", maxw=170)
                y += rh_lit
    f.text(50, H - 62, f"{n_shown} of the {len(stmts) - 1} properties of the observation are drawn; left out: " + ", ".join(left_out) + ".", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "One node, three vocabularies: the SOSA view and the CRM view need no value of the third, and a reader of either finds the same observation.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"node": cur(obs), "shown": n_shown, "properties": len(stmts) - 1, "left_out": left_out,
               "measured": float(one(G.measuredValue)), "median": float(one(G.smoothedValue_rollingMedian)), "savgol": float(one(G.smoothedValue_savgol))}


# ------------------------------------------------------------------ measured and smoothed

def series_fig(D: MeasData, outdir: Path, name: str, zoom_ka: float = 60.0) -> tuple[Fig, dict]:
    s = D.series
    ages = [r[0] for r in s]
    lo = min(min(r[1:4]) for r in s)
    hi = max(max(r[1:4]) for r in s)
    y_lo, y_hi = math.floor(lo / 100) * 100, math.ceil(hi / 100) * 100
    left, right = 150, 1650
    W, H = 1750, 1120
    steps = sorted(b - a for a, b in zip(ages, ages[1:]))
    gap = 8 * steps[len(steps) // 2]                       # a stretch with no observations is left open, not bridged by a line
    holes = [(a, b) for a, b in zip(ages, ages[1:]) if b - a > gap]
    f = Fig(name, "Measured and smoothed methane", W, H, outdir)
    f.text(50, 40, "The measured value stays; the smoothed values are two more statements about it", 26, True, anchor="start")
    f.text(50, 76, "geolod:measuredValue, geolod:smoothedValue_rollingMedian and geolod:smoothedValue_savgol of the methane observations, against age.", 19, color=MUTED, anchor="start", maxw=W - 100)

    def panel(top, bottom, x0, x1, pts, title, dots=True, tick=100, xtick=100, shade=()):
        X = lambda a: round(left + (right - left) * (a - x0) / (x1 - x0), 1)
        Y = lambda v: round(bottom - (v - y_lo) / (y_hi - y_lo) * (bottom - top), 1)
        f.text(left, top - 30, title, 19, True, anchor="start")
        for a, b in shade:
            f.rect(X(a), top, round(X(b) - X(a), 1), bottom - top, "#f1efe8")
            f.text((X(a) + X(b)) / 2, (top + bottom) / 2, f"no observations, {a:.0f} to {b:.0f} ka BP", 17, color=MUTED)
        for v in range(y_lo, y_hi + 1, tick):
            f.line(left, Y(v), right, Y(v), None, w=1, color=GRID)
            f.text(left - 14, Y(v), str(v), 16, color=MUTED, anchor="end")
        t = math.ceil(x0 / xtick) * xtick
        while t <= x1 + 1e-9:
            f.line(X(t), bottom, X(t), bottom + 7, None, w=1, color=MUTED)
            f.text(X(t), bottom + 24, f"{t:g}", 16, color=MUTED)
            t += xtick
        f.text(right, bottom + 52, "age, ka BP", 16, color=MUTED, anchor="end")
        f.text(left - 14, top - 30, "ppbv", 16, color=MUTED, anchor="end")
        if dots:
            for a, m, _, _, _ in pts:
                f.raw(f'<circle cx="{X(a)}" cy="{Y(m)}" r="2.6" fill="{RAW_COLOUR}" fill-opacity=".75"/>')
        for k, colour in ((2, MEDIAN_COLOUR), (3, SAVGOL_COLOUR)):
            d = " ".join(("M" if i == 0 or r[0] - pts[i - 1][0] > gap else "L") + f"{X(r[0])} {Y(r[k])}" for i, r in enumerate(pts))
            f.raw(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{1.4 if not dots else 2.4}" stroke-linejoin="round"/>')
        return X, Y

    panel(150, 400, 0, ages[-1], s, f"The whole record, {len(s)} observations", dots=False, shade=holes)
    near = [r for r in s if r[0] <= zoom_ka]
    X, Y = panel(560, 920, 0, zoom_ka, near, f"The first {zoom_ka:g} ka, {len(near)} observations", xtick=10, tick=100)
    a0, m0, med0, sg0, _ = near[0]
    for v, text, colour in ((m0, f"measured {m0:g}", RAW_COLOUR), (med0, f"rolling median {med0:g}", MEDIAN_COLOUR), (sg0, f"Savitzky-Golay {sg0:.1f}", SAVGOL_COLOUR)):
        f.raw(f'<circle cx="{X(a0)}" cy="{Y(v)}" r="6" fill="none" stroke="{colour}" stroke-width="2.2"/>')
    order = sorted(((m0, f"measured {m0:g}", RAW_COLOUR), (med0, f"rolling median {med0:g}", MEDIAN_COLOUR), (sg0, f"Savitzky-Golay {sg0:.1f}", SAVGOL_COLOUR)), key=lambda t: -t[0])
    for i, (v, text, colour) in enumerate(order):
        ly = 575 + i * 24
        f.line(X(a0) + 8, Y(v), left + 70, ly, None, w=.8, color=MUTED)
        f.text(left + 78, ly, f"first observation, {text}", 17, anchor="start", color=colour if colour != RAW_COLOUR else "#4a4a46")
    ly = 1015
    for i, (colour, text, dot) in enumerate(((RAW_COLOUR, "measured value", True), (MEDIAN_COLOUR, "rolling median, window 11", False), (SAVGOL_COLOUR, "Savitzky-Golay, window 11, order 2", False))):
        x = left + [0, 330, 730][i]
        if dot:
            f.raw(f'<circle cx="{x + 11}" cy="{ly}" r="5" fill="{colour}" fill-opacity=".75"/>')
        else:
            f.line(x, ly, x + 24, ly, None, w=3, color=colour)
        f.text(x + 34, ly, text, 18, color=MUTED, anchor="start")
    span = (ages[-1] - ages[0]) / (len(s) - 1) * 10
    f.text(50, H - 62, f"{len(s)} observations over {ages[0]:g} to {ages[-1]:.0f} ka BP. A window of 11 points is about {span:.1f} ka on average along this record.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "Both filters lean on neighbours: at the first observation there are none on one side, which is why the three values differ most there.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"n": len(s), "first_age": ages[0], "last_age": ages[-1], "near": len(near), "span": span,
               "first": (m0, med0, sg0), "holes": holes, "rows": [(round(a, 4), m, med, sg) for a, m, med, sg, _ in s]}


# ------------------------------------------------------------------ which kinds of value each dataset has

def coverage_fig(D: MeasData, outdir: Path, name: str) -> tuple[Fig, dict]:
    rows = D.datasets
    left, top, rowh = 60, 190, 74
    cx = [600, 860, 1000, 1180, 1360, 1540]          # unit, observations, then the four kinds of value
    W, H = 1750, top + rowh * len(rows) + 150
    f = Fig(name, "Which values each dataset carries", W, H, outdir)
    f.text(50, 40, "Every observation has its value and two smoothed ones; only methane has a standard deviation", 26, True, anchor="start")
    f.text(50, 76, "Observations of each geolod:IceCoreDataset that carry each kind of value, counted on the node.", 19, color=MUTED, anchor="start", maxw=W - 100)
    f.text(left, top - 34, "Dataset", 17, True, anchor="start")
    f.text(cx[0], top - 34, "unit", 17, True, anchor="start")
    f.text(cx[1] + 70, top - 34, "observations", 17, True, anchor="end")
    for i, (_, lab) in enumerate(VALUE_KINDS):
        f.text(cx[2 + i] + 70, top - 34, lab, 17, True)
    for i, d in enumerate(rows):
        y = top + i * rowh
        if i % 2 == 0:
            f.rect(50, y, W - 100, rowh, "#f6f6f3")
        f.text(left, y + rowh / 2 - 12, d["title"], 19, True, anchor="start", maxw=540)
        f.text(left, y + rowh / 2 + 14, d["key"], 15, color=MUTED, anchor="start")
        f.text(cx[0], y + rowh / 2, d["unit"], 18, anchor="start")
        f.text(cx[1] + 70, y + rowh / 2, f"{d['n']:,}", 19, anchor="end")
        for j, (k, _) in enumerate(VALUE_KINDS):
            c = d["counts"][k]
            x = cx[2 + j]
            if c == d["n"]:
                fill, ink = "#0072B2", "#ffffff"
            elif c:
                fill, ink = "#E69F00", INK
            else:
                fill, ink = "#ffffff", "#9a988f"
            f.rect(x, y + 14, 140, rowh - 28, fill, BLACK if c else "#bdbbb2", 5, 1)
            f.text(x + 70, y + rowh / 2, f"{c:,}" if c else "none", 18, c > 0, ink)
    ly = top + rowh * len(rows) + 36
    for x, (fill, text) in zip((left, left + 360, left + 760), (("#0072B2", "all observations of the dataset"), ("#E69F00", "some of them"), ("#ffffff", "none"))):
        f.rect(x, ly - 11, 22, 22, fill, BLACK if fill != "#ffffff" else "#bdbbb2", 3)
        f.text(x + 32, ly, text, 18, color=MUTED, anchor="start")
    total = sum(d["n"] for d in rows)
    f.text(50, H - 62, f"{total:,} observations in five datasets. The speleothem observations (geolod:SpeleothemObservation and its two subclasses) are in the large graph of the pipeline.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "The two smoothed values sit under two property names of their own (smoothedValue_rollingMedian, smoothedValue_savgol), one per filter, not under one generic property.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"rows": {d["key"]: (d["n"], tuple(d["counts"][k] for k, _ in VALUE_KINDS), d["unit"]) for d in rows}, "total": total}
