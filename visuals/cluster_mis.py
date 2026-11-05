"""Figures of the cluster page "Marine isotope stages".

The data come from two committed graphs: `ontology/vocab/mis.ttl` (the stage concepts and, per stage, the boundary ages
of every source as geolod:MISAttributeAssignment) and `EPICA/rdf/epica_dome_c.ttl` (the membership of every observation
in a stage, and the depth of a stage boundary on each EPICA timescale). The temporal reference systems are labelled in
`ontology/trs.ttl`. Every number printed on a figure is counted from there; nothing is typed in.

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS

import model_data as md
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
G = Namespace("http://w3id.org/geo-lod/")
TRS = Namespace("http://w3id.org/geo-lod/trs/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
TIME = Namespace("http://www.w3.org/2006/time#")
PROV = Namespace("http://www.w3.org/ns/prov#")
BLACK, GRID, INK = "#000000", "#d8d6ce", "#1f1f1d"

# Okabe-Ito again; the five EPICA timescales keep one colour on every figure of the page.
TRS_ORDER = ["EDC2-gas", "EDC2-ice", "EDC3-ice", "AICC2023-ice", "AICC2023-gas"]
TRS_COLOUR = {"EDC2-gas": "#0072B2", "EDC2-ice": "#56B4E9", "EDC3-ice": "#009E73", "AICC2023-ice": "#E69F00", "AICC2023-gas": "#D55E00"}
RAILSBACK = "source_railsback2015"
LR04 = "source_lisieckiRaymo2005"


def _stage_no(iri) -> int | None:
    """The number of a numbered stage (MIS_5); None for the LR04 stage names that carry a letter (MIS_G1)."""
    tail = str(iri).rsplit("MIS_", 1)[1].split("_")[0]
    return int(tail) if tail.isdigit() else None


def _local(iri) -> str:
    return str(iri).rsplit("/", 1)[1]


class MisData:
    """The MIS vocabulary, the EPICA graph and the timescale labels, read once. `g` holds both graphs, for the queries."""

    def __init__(self, repo: Path = REPO):
        vocab = Graph().parse(repo / "ontology/vocab/mis.ttl", format="turtle")
        epica = Graph().parse(repo / "EPICA/rdf/epica_dome_c.ttl", format="turtle")
        trs = Graph().parse(repo / "ontology/trs.ttl", format="turtle")
        g = Graph()
        for src in (vocab, epica):
            for t in src:
                g.add(t)
        self.g, self.vocab, self.epica = g, vocab, epica
        for pfx, ns in (("geolod", G), ("crm", CRM), ("time", TIME), ("prov", PROV), ("trs", TRS)):
            g.bind(pfx, ns)
        self.trs_label = {k: str(next(trs.objects(TRS[k], RDFS.label))).split(", EPICA")[0] for k in TRS_ORDER}

        # Boundary depths: (stage no, timescale key, depth m, age ka BP of the boundary as Railsback et al. give it)
        self.depths: list[tuple[int, str, float, float]] = []
        for a in epica.subjects(RDF.type, G.MISAttributeAssignment):
            if next(epica.objects(a, CRM.P177_assigned_property_of_type)) != G.MISBoundaryDepth:
                continue
            stage = next(epica.objects(a, CRM.P140_assigned_attribute_to))
            if _stage_no(stage) is None:
                continue
            trs_key = _local(next(epica.objects(a, G.inChronology)))
            depth = float(next(g.objects(next(epica.objects(a, CRM.P141_assigned)), G.atDepth_m)))
            tp = next(epica.objects(a, PROV.wasDerivedFrom))
            self.depths.append((_stage_no(stage), trs_key, depth, float(next(vocab.objects(tp, G.ageKaBP)))))
        self.depths.sort()

        # Stage boundaries by source, for the stages that have a competing reading:
        # stage no -> {"mode": warm/cold, "leading": ka, "alt": ka}
        reading: dict[int, dict] = defaultdict(dict)
        for a in vocab.subjects(RDF.type, G.MISAttributeAssignment):
            if next(vocab.objects(a, CRM.P177_assigned_property_of_type)) != G.PeriodBeginning:
                continue
            stage = next(vocab.objects(a, CRM.P140_assigned_attribute_to))
            if (stage, RDF.type, G.MarineIsotopeStage) not in vocab or _stage_no(stage) is None:
                continue
            status = _local(next(vocab.objects(a, G.assignmentStatus)))
            age = float(next(vocab.objects(next(vocab.objects(a, CRM.P141_assigned)), TIME.numericPosition)))
            reading[_stage_no(stage)][status] = (age, _local(next(vocab.objects(a, DCTERMS.source))))
            reading[_stage_no(stage)]["mode"] = _local(next(vocab.objects(stage, G.climateMode)))
        self.competing = {n: r for n, r in sorted(reading.items()) if "AlternativeAssignment" in r}

        # Memberships: (observation, timescale key, stage no)
        self.members = [(str(next(epica.objects(a, CRM.P140_assigned_attribute_to))), _local(next(epica.objects(a, G.inChronology))),
                         _stage_no(next(epica.objects(a, CRM.P141_assigned))))
                        for a in epica.subjects(RDF.type, G.MISMembershipAssignment)]
        if not self.depths or not self.competing or not self.members:
            raise ValueError("the MIS graphs hold no boundary depths, no competing boundaries or no memberships; the figures have nothing to draw")


# ------------------------------------------------------------------ the pattern

def mis_pattern_fig(M: md.Model, D: MisData, outdir: Path, name: str) -> tuple[Fig, dict]:
    """Two assignments, one stage: the membership of an observation, and a boundary of the stage on a timescale.

    Both patterns are read from the graph (one real node each); the CRM anchor of the two classes from the ontology."""
    by = {c.curie: c for c in M.classes.values()}
    for need in ("geolod:MISMembershipAssignment", "geolod:MISAttributeAssignment", "geolod:MarineIsotopeStage", "geolod:IceCoreObservation",
                 "geolod:DepthPosition"):
        if need not in by:
            raise ValueError(f"{name}: {need} is not a class of the ontology")
    anc = {k: M.curie(M.anchors(by[k].iri)[0][0]) for k in ("geolod:MISMembershipAssignment", "geolod:MISAttributeAssignment")}
    g = D.epica
    nm = g.namespace_manager
    cur = lambda t: t.n3(nm) if isinstance(t, URIRef) else str(t)
    member = next(a for a in sorted(g.subjects(RDF.type, G.MISMembershipAssignment)) if _local(a) == "mis_membership_ch4_0001")
    bound = next(a for a in sorted(g.subjects(RDF.type, G.MISAttributeAssignment)) if _local(a) == "mis_boundary_depth_ch4_11_begin")

    def props(a, preds):
        return [(cur(p), cur(o)) for p in preds for o in g.objects(a, p)]

    def typ(n):
        """The geo-lod class of a node (skos:Concept and owl:NamedIndividual come second)."""
        return cur(sorted(D.g.objects(n, RDF.type), key=lambda t: (not str(t).startswith(str(G)), str(t)))[0])

    W, H = 1750, 1340
    f = Fig(name, "Two assignments, one stage", W, H, outdir)
    f.text(50, 40, "A stage is attached twice: to an observation, and to a depth", 26, True, anchor="start")
    f.text(50, 76, "Both are a crm:E13 Attribute Assignment, so the source, the timescale and the status stay with the statement.", 19, color=MUTED, anchor="start")
    gl, own = F.OWN_FILL["geolod"], "#f6f6f3"

    def node(x, y, w, h, title, sub=None, fill="#ffffff", tsz=19):
        f.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{BLACK}" stroke-width="1.2"/>')
        if sub:
            f.text(x + w / 2, y + h / 2 - 10, title, tsz, True, BLACK, maxw=w - 12)
            f.text(x + w / 2, y + h / 2 + 14, sub, 14, color="#3a3935", maxw=w - 10)
        else:
            f.text(x + w / 2, y + h / 2, title, tsz, True, BLACK, maxw=w - 12)

    def arrow(x1, y1, x2, y2, label, lx=None, ly=None):
        f.line(round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1), "a")
        w = tw(label, 17) + 12
        cx, cy = (lx if lx is not None else (x1 + x2) / 2), (ly if ly is not None else (y1 + y2) / 2)
        f.rect(round(cx - w / 2, 1), round(cy - 12, 1), round(w, 1), 24, "#ffffff", "none", 4)
        f.text(round(cx, 1), round(cy, 1), label, 17, color=MUTED)

    def block(y0, title, assign, left, right, left_edge, right_edge, preds, anchor_key, note):
        f.text(50, y0, title, 22, True, anchor="start")
        ay = y0 + 70
        node(50, ay, 330, 66, left[0], left[1], gl)
        node(700, ay, 470, 74, cur(assign), f"a {typ(assign)}  → {anc[anchor_key]}", gl)
        node(1370, ay, 350, 66, right[0], right[1], gl if right[1].startswith("a geolod:") else own)
        arrow(700, ay + 30, 380, ay + 30, left_edge)
        arrow(1170, ay + 37, 1370, ay + 33, right_edge)
        rows = props(assign, preds)
        for i, (p, o) in enumerate(rows):
            y = ay + 120 + i * 62
            node(700, y, 470, 50, o, None, own, 17)
            f.line(700, y + 25, 650, y + 25, None, w=1.2)
            f.text(640, y + 25, p, 17, color=MUTED, anchor="end")
        line, k = "", 0
        for word in note.split():
            if line and tw(line + " " + word, 17) > 480:
                f.text(1210, ay + 130 + k * 26, line, 17, color="#9a3412", anchor="start")
                line, k = word, k + 1
            else:
                line = (line + " " + word).strip()
        f.text(1210, ay + 130 + k * 26, line, 17, color="#9a3412", anchor="start")
        return ay + 120 + len(rows) * 62

    obs = next(g.objects(member, CRM.P140_assigned_attribute_to))
    stage = next(g.objects(member, CRM.P141_assigned))
    y1 = block(130, "Which stage an observation falls in", member,
               (cur(obs), f"a {typ(obs)}"), (cur(stage), f"a {typ(stage)}"), "crm:P140_assigned_attribute_to", "crm:P141_assigned",
               [CRM.P177_assigned_property_of_type, G.inChronology, DCTERMS.source, G.assignmentStatus], "geolod:MISMembershipAssignment",
               "The scale is the one the record is dated on; the observation has one membership.")
    f.line(50, y1 + 22, W - 50, y1 + 22, None, w=1.2, color=GRID)
    stage2 = next(g.objects(bound, CRM.P140_assigned_attribute_to))
    dpos = next(g.objects(bound, CRM.P141_assigned))
    dval = next(g.objects(dpos, G.atDepth_m))
    y2 = block(y1 + 70, "Where a stage begins on a timescale", bound,
               (cur(stage2), f"a {typ(stage2)}"), (cur(dpos), f"a {typ(dpos)}  ·  {float(dval):.3f} m"), "crm:P140_assigned_attribute_to", "crm:P141_assigned",
               [CRM.P177_assigned_property_of_type, G.inChronology, DCTERMS.source, G.assignmentStatus, G.interpolationMethod, PROV.wasDerivedFrom],
               "geolod:MISAttributeAssignment", "One such node per timescale; the age of the boundary stays the same.")
    both = anc["geolod:MISMembershipAssignment"] if anc["geolod:MISMembershipAssignment"] == anc["geolod:MISAttributeAssignment"] else \
        f"{anc['geolod:MISMembershipAssignment']} and {anc['geolod:MISAttributeAssignment']}"
    f.text(50, H - 70, f"The ontology anchors both classes in {both}; nodes and values are read from the committed graphs.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 40, "The stage concept also carries geolod:beginAgeKaBP of the leading source as a shortcut; a competing reading exists only as an assignment.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"membership": cur(member), "boundary": cur(bound)}


# ------------------------------------------------------------------ one boundary, five depths

def boundary_depth_fig(D: MisData, outdir: Path, name: str) -> tuple[Fig, dict]:
    stages = sorted({s for s, *_ in D.depths})
    cell, rowh, left, top = 190, 34, 360, 170
    W = left + cell * len(TRS_ORDER) + 330
    H = top + rowh * len(stages) + 120
    f = Fig(name, "The same stage boundary at different depths", max(W, 1750), H, outdir)
    W = f.w
    f.text(50, 40, "One boundary, one age, up to five depths", 26, True, anchor="start")
    f.text(50, 76, "The beginning of each stage as Railsback et al. (2015) date it; the depth is geolod:atDepth_m of the node a "
           "geolod:MISAttributeAssignment points to, one per timescale.", 19, color=MUTED, anchor="start", maxw=W - 100)
    val = {(s, t): d for s, t, d, _ in D.depths}
    age = {s: a for s, _, _, a in D.depths}
    spread = {}
    for j, t in enumerate(TRS_ORDER):
        f.text(left + cell * j + cell / 2, top - 34, D.trs_label[t].replace(" age", ""), 16, True, anchor="middle", maxw=cell - 6)
        f.raw(f'<circle cx="{left + cell * j + cell / 2}" cy="{top - 12}" r="6" fill="{TRS_COLOUR[t]}" stroke="{BLACK}" stroke-width="1"/>')
    f.text(left + cell * len(TRS_ORDER) + 20, top - 24, "Spread between scales", 16, True, anchor="start")
    maxsp = 0.0
    for s in stages:
        ds = [val[(s, t)] for t in TRS_ORDER if (s, t) in val]
        spread[s] = max(ds) - min(ds)
        maxsp = max(maxsp, spread[s])
    bx = left + cell * len(TRS_ORDER) + 20
    for i, s in enumerate(stages):
        y = top + i * rowh
        if i % 2 == 0:
            f.rect(50, y, W - 100, rowh, "#f6f6f3")
        f.text(60, y + rowh / 2, f"Beginning of MIS {s}", 17, True, anchor="start", maxw=200)
        f.text(left - 14, y + rowh / 2, f"{age[s]:g} ka BP", 17, color=MUTED, anchor="end")
        for j, t in enumerate(TRS_ORDER):
            cx = left + cell * j + cell / 2
            if (s, t) in val:
                f.raw(f'<circle cx="{cx - 52}" cy="{y + rowh / 2}" r="6" fill="{TRS_COLOUR[t]}" stroke="{BLACK}" stroke-width="1"/>')
                f.text(cx - 38, y + rowh / 2, f"{val[(s, t)]:.1f} m", 17, anchor="start")
            else:
                f.text(cx, y + rowh / 2, "·", 17, color="#b5b3aa")
        if spread[s] > 0:
            f.rect(bx, y + 8, round(240 * spread[s] / maxsp, 1), rowh - 16, "#9a3412", BLACK, 0, 1)
            f.text(bx + round(240 * spread[s] / maxsp, 1) + 8, y + rowh / 2, f"{spread[s]:.0f} m", 16, anchor="start")
    f.text(50, H - 60, "A dot in the place of a depth: the record does not reach that stage on that scale. Spread = deepest minus shallowest depth of the same boundary.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "The five scales date different records (gas or ice phase of the same core), so the depths differ although the age is the same.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    widest = max(stages, key=lambda s: spread[s])
    return f, {"rows": sorted(D.depths), "assignments": len(D.depths), "boundaries": len(stages), "widest": widest, "spread": spread[widest]}


# ------------------------------------------------------------------ two sources, one boundary

def stage_sources_fig(D: MisData, outdir: Path, name: str) -> tuple[Fig, dict]:
    rows = sorted(D.competing)
    rowh, left, top = 27, 600, 170
    px0, px1 = left, 1500          # the plot, in px
    lo, hi = -10.0, 25.0
    X = lambda v: round(px0 + (v - lo) / (hi - lo) * (px1 - px0), 1)
    W, H = 1750, top + rowh * len(rows) + 130
    f = Fig(name, "Where the two sources date a stage boundary differently", W, H, outdir)
    f.text(50, 40, "Two sources, one boundary: Railsback et al. against LR04", 26, True, anchor="start")
    f.text(50, 76, "The beginning of 28 stages has a leading reading (Railsback et al. 2015) and an alternative one (LR04); both stay in the graph.", 19, color=MUTED, anchor="start", maxw=W - 100)
    for v in range(-10, 26, 5):
        f.line(X(v), top - 10, X(v), top + rowh * len(rows), None, w=1.8 if v == 0 else 1, color=INK if v == 0 else GRID)
        f.text(X(v), top - 26, f"{v:+d}" if v else "0", 16, color=MUTED)
    f.text((px0 + px1) / 2, top - 62, "LR04 minus Railsback et al., ka", 17, True, color=MUTED)
    f.text(left - 14, top - 62, "Leading reading", 16, True, color=MUTED, anchor="end")
    dev = {}
    for i, n in enumerate(rows):
        y = top + i * rowh
        r = D.competing[n]
        if i % 2 == 0:
            f.rect(50, y, W - 100, rowh, "#f6f6f3")
        f.rect(60, y + 5, 22, rowh - 10, "url(#warm)" if r["mode"].endswith("Warm") else "url(#cold)", BLACK, 3, .8)
        f.text(96, y + rowh / 2, f"Beginning of MIS {n}", 17, True, anchor="start", maxw=190)
        f.text(left - 14, y + rowh / 2, f"{r['LeadingAssignment'][0]:g} ka BP", 17, color=MUTED, anchor="end")
        d = round(r["AlternativeAssignment"][0] - r["LeadingAssignment"][0], 6)
        dev[n] = d
        f.line(X(0), y + rowh / 2, X(d), y + rowh / 2, None, w=2.4, color="#9a3412")
        f.raw(f'<circle cx="{X(d)}" cy="{y + rowh / 2}" r="6" fill="#9a3412" stroke="{BLACK}" stroke-width="1"/>')
        if abs(d) >= 5:
            f.text(X(d) + (12 if d > 0 else -12), y + rowh / 2, f"{d:+.1f}", 16, True, anchor="start" if d > 0 else "end")
    big = sorted(dev, key=lambda n: -abs(dev[n]))
    f.text(1530, top + 40, "Largest gaps", 17, True, anchor="start")
    for k, n in enumerate(big[:4]):
        f.text(1530, top + 72 + k * 28, f"MIS {n}: {dev[n]:+.1f} ka", 17, anchor="start")
    f.text(50, H - 60, "Stripes: warm stage (dots) and cold stage (hatching) as the vocabulary classes them. The boundary of a stage is the end of the one before it, so each is drawn once.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "Neither reading is erased: the alternative one is a geolod:AlternativeAssignment next to the leading one.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"stages": len(rows), "dev": dev, "within1": sum(1 for d in dev.values() if abs(d) <= 1.0), "big": big[:4]}


# ------------------------------------------------------------------ memberships per timescale

def memberships_fig(D: MisData, outdir: Path, name: str) -> tuple[Fig, dict]:
    counts = defaultdict(int)
    obs_n = defaultdict(set)
    for o, t, _ in D.members:
        counts[t] += 1
        obs_n[t].add(o)
    total = len(D.members)
    order = sorted(TRS_ORDER, key=lambda t: -counts[t])
    left, barw, top, rowh = 380, 900, 150, 64
    W, H = 1750, top + rowh * len(order) + 130
    f = Fig(name, "Stage memberships per timescale", W, H, outdir)
    f.text(50, 40, "Which timescale each stage membership is stated on", 26, True, anchor="start")
    f.text(50, 76, f"{total} geolod:MISMembershipAssignment in the EPICA graph; each observation has one, on the scale its record is dated on.", 19, color=MUTED, anchor="start")
    for t in range(0, 101, 25):
        x = left + barw * t / 100
        f.line(x, top - 14, x, top + rowh * len(order) - 8, None, w=1, color=GRID)
        f.text(x, top - 30, f"{t} %", 16, color=MUTED)
    for i, t in enumerate(order):
        y = top + i * rowh
        share = counts[t] / total
        f.text(left - 18, y + rowh / 2 - 8, D.trs_label[t], 19, True, anchor="end", maxw=left - 40)
        f.rect(left, y + 8, barw, rowh - 32, "#eeede8")
        f.rect(left, y + 8, round(barw * share, 1), rowh - 32, TRS_COLOUR[t], BLACK, 0, 1)
        f.text(left + barw + 18, y + rowh / 2 - 8, f"{counts[t]}  ·  {100 * share:.0f} %", 20, anchor="start")
    f.text(50, H - 30, "The share follows the number of measurements of the records dated on each scale, not a choice between scales.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"total": total, "counts": dict(counts), "observations": sum(len(v) for v in obs_n.values())}
