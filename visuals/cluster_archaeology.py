"""Figures of the cluster page "Archaeology and the Campanian Ignimbrite".

The data come from four committed graphs: `CI/rdf/ci_findspots.ttl` (74 findspots of Campanian Ignimbrite tephra),
`CI/rdf/ci_site_annotations.ttl` (the three of them read for archaeology), `SISAL/rdf/sisal_sites.ttl` (365 caves) and
`SISAL/rdf/sisal_site_annotations.ttl` (305 caves screened, 37 with archaeological evidence), together with the ontology
files that define the classes. Every number printed on a figure is counted from the graphs; nothing is typed in.

The coastline under the map is Natural Earth land (`data/raw/basemap/ne_50m_land.geojson`, public domain), read with the
standard library by `ontology/geo_lod_basemap.py` and clipped to the window.

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SKOS

import cluster_cards as CC
import model_data as md
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "ontology"))
import geo_lod_basemap as BM  # noqa: E402

G = Namespace("http://w3id.org/geo-lod/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
CI = Namespace("http://w3id.org/geo-lod/ci/")
BLACK, GRID, INK = "#000000", "#d8d6ce", "#1f1f1d"
# Okabe-Ito: evidence, screened without evidence, no statement
EVIDENCE, TYPED_ONLY, SCREENED, SILENT = "#0072B2", "#56B4E9", "#E69F00", "#d9d7cf"
CONFIDENCE = [("high", "#0072B2"), ("medium", "#56B4E9"), ("low", "#E69F00")]
LEVEL_COLOUR = {"high": "#009E73", "medium": "#56B4E9", "low": "#E69F00", "dubious": "#D55E00", "representative": "#CC79A7", "none": "#8a8a85"}
LEVEL_ORDER = ["high", "medium", "low", "dubious", "representative"]
CONTEXT_ORDER = ["PalaeolithicContext", "PrehistoricContext", "PalaeontologicalContext", "HistoricContext", "MesoamericanContext"]
WKT = re.compile(r"POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)")
EXAMPLE_CAVE, EXAMPLE_PLAIN = "Cave_site_0077", "cisite_1"        # Chauvet cave, and a findspot nobody has read for archaeology


def _local(iri) -> str:
    return str(iri).rsplit("/", 1)[-1]


def _point(wkt) -> tuple[float, float]:
    m = WKT.search(str(wkt))
    if not m:
        raise ValueError(f"not a WKT point: {wkt}")
    return float(m.group(1)), float(m.group(2))


class ArchData:
    """The CI and SISAL graphs with their annotations and the ontology files in one graph `g` for the queries."""

    def __init__(self, repo: Path = REPO):
        self.ci = Graph().parse(repo / "CI/rdf/ci_findspots.ttl", format="turtle")
        self.cia = Graph().parse(repo / "CI/rdf/ci_site_annotations.ttl", format="turtle")
        self.ss = Graph().parse(repo / "SISAL/rdf/sisal_sites.ttl", format="turtle")
        self.sa = Graph().parse(repo / "SISAL/rdf/sisal_site_annotations.ttl", format="turtle")
        g = Graph()
        for src in (self.ci, self.cia, self.ss, self.sa):
            for t in src:
                g.add(t)
        for rel in ("ontology/geo_lod_core.ttl", "SISAL/rdf/sisal_ontology.ttl"):
            for t in Graph().parse(repo / rel, format="turtle"):
                g.add(t)
        for pfx, ns in (("geolod", G), ("geo", GEO), ("crm", CRM), ("prov", PROV), ("rdfs", RDFS), ("owl", OWL), ("skos", SKOS), ("dct", DCTERMS), ("ci", CI),
                        ("crmgeo", Namespace("http://www.ics.forth.gr/isl/CRMgeo/")), ("crmarchaeo", Namespace("http://www.cidoc-crm.org/extensions/crmarchaeo/"))):
            g.bind(pfx, ns)
        # the example nodes carry the namespaces of their own files
        for src in (self.ci, self.cia, self.ss, self.sa):
            for pfx, ns in src.namespaces():
                if pfx and pfx not in dict(g.namespaces()):
                    g.bind(pfx, ns)
        self.g, self.repo = g, repo
        caves = set(self.ss.subjects(RDF.type, G.Cave))
        findspots = set(self.ci.subjects(RDF.type, G.CIFindspot))
        self.n_caves, self.n_ci = len(caves), len(findspots)
        cave_scr = caves & set(self.sa.subjects(G.screenedForArchaeology, None))
        cave_pos = caves & set(self.sa.subjects(RDF.type, G.ArchaeologicalCaveSite))
        ci_scr = findspots & set(self.cia.subjects(G.screenedForArchaeology, None))
        # the findspot file types a findspot as archaeological from the source's own list; the annotation file holds the
        # curated reading (context, category, confidence, screened) of some of them
        ci_pos = findspots & set(self.ci.subjects(RDF.type, G.CIArchaeologicalSite))
        self.cave_screened, self.cave_positive, self.cave_curated = len(cave_scr), len(cave_pos), len(cave_pos & cave_scr)
        self.ci_screened, self.ci_positive, self.ci_curated = len(ci_scr), len(ci_pos), len(ci_pos & ci_scr)
        # context x confidence, per strand
        self.contexts: dict[tuple[str, str, str], int] = defaultdict(int)
        for strand, ann, cls in (("cave", self.sa, G.ArchaeologicalCaveSite), ("CI", self.cia, G.CIArchaeologicalSite)):
            for s in ann.subjects(RDF.type, cls):
                ctx, conf = ann.value(s, G.archaeologicalBroaderContext), ann.value(s, G.archaeologicalConfidence)
                if ctx is None or conf is None:
                    raise ValueError(f"{s} is an archaeological site without context or confidence")
                self.contexts[(strand, _local(ctx), str(conf))] += 1
        # the map
        self.findspots = []        # (local, lon, lat, level, typed archaeological, curated reading)
        arch, curated = ci_pos, ci_scr
        for s in sorted(findspots):
            geom = self.ci.value(s, GEO.hasGeometry)
            lon, lat = _point(self.ci.value(geom, GEO.asWKT))
            level = self.ci.value(geom, G.hasCertaintyLevel)
            self.findspots.append((_local(s), lon, lat, _local(level) if level is not None else "none", s in arch, s in curated))
        self.arch_caves = []       # (local, label, lon, lat)
        for c in sorted(set(self.sa.subjects(RDF.type, G.ArchaeologicalCaveSite)) & caves):
            lon, lat = _point(self.ss.value(self.ss.value(c, GEO.hasGeometry), GEO.asWKT))
            self.arch_caves.append((_local(c), str(self.ss.value(c, RDFS.label)), lon, lat))
        if not self.findspots or not self.arch_caves:
            raise ValueError("the committed graphs hold no findspots or archaeological caves; the figures have nothing to draw")


# ------------------------------------------------------------------ one reading, three nodes

def pattern_fig(M: md.Model, D: ArchData, outdir: Path, name: str) -> tuple[Fig, dict]:
    g = D.g
    nm = g.namespace_manager
    cave, cia = G[EXAMPLE_CAVE], next(iter(sorted(D.cia.subjects(RDF.type, G.CIArchaeologicalSite))))
    plain = CI[EXAMPLE_PLAIN]
    if (cave, RDF.type, G.ArchaeologicalCaveSite) not in g or (plain, RDF.type, G.CIFindspot) not in g:
        raise ValueError(f"{name}: the example nodes are not in the committed graphs")
    if (plain, G.screenedForArchaeology, None) in g:
        raise ValueError(f"{name}: {plain} has been screened; it no longer shows a finding nobody has read")
    cur = lambda t: t.n3(nm)
    wd = lambda v: "wikidata:" + str(v).rsplit("/", 1)[-1]

    def reading(site, label_graph):
        label = label_graph.value(site, RDFS.label) or D.ss.value(site, RDFS.label)
        src = label_graph.value(site, PROV.wasDerivedFrom)
        rows = [("rdfs:label", "lit", str(label), "") if label is not None else CC.card_row(g, site, SKOS.note, "lit"),
                CC.card_row(g, site, G.archaeologicalBroaderContext, "node"), CC.card_row(g, site, G.archaeologicalCategory, "lit"),
                CC.card_row(g, site, G.archaeologicalConfidence, "lit"), CC.card_row(g, site, G.screenedForArchaeology, "lit")]
        # a node may have several links (Wikidata and OpenStreetMap); take the Wikidata one, else the first in sorted order
        pred = OWL.sameAs if (site, OWL.sameAs, None) in g else SKOS.closeMatch
        links = sorted(g.objects(site, pred), key=lambda o: (not str(o).startswith("http://www.wikidata.org/"), str(o)))
        if links:
            rows.append((pred.n3(g.namespace_manager), "lit", wd(links[0]), ""))
        rows.append(("prov:wasDerivedFrom", "node", cur(src), CC.node_class(g, src, nm)))
        return rows

    geom = g.value(plain, GEO.hasGeometry)
    src = g.value(plain, PROV.wasDerivedFrom)
    plain_rows = [CC.card_row(g, plain, RDFS.label, "lit"), CC.card_row(g, plain, G.hasLiteratureReference, "lit"),
                  ("geolod:screenedForArchaeology", "lit", "no statement", ""),
                  CC.card_row(g, plain, GEO.hasGeometry, "node"),
                  ("geolod:hasCertaintyLevel", "lit", CC.card_row(g, geom, G.hasCertaintyLevel, "node")[2].split(":")[-1] + ", on the geometry", ""),
                  ("prov:wasDerivedFrom", "node", CC.short_iri(src), "a repository, no node of its own in the graph")]
    panels = [
        (f"A cave, read: {cur(cave)}", "geolod:ArchaeologicalCaveSite, a geolod:Cave and a crmarchaeo:A2", reading(cave, D.sa)),
        (f"A findspot, read: {cur(cia)}", "geolod:CIArchaeologicalSite, a geolod:CIFindspot and a crmarchaeo:A2", reading(cia, D.cia)),
        (f"A findspot, not read: {cur(plain)}", "geolod:CIFindspot only: no statement about archaeology", plain_rows),
    ]
    W, pw, gap, x0 = 1900, 590, 30, 50
    ph = max(CC.card_height(r) for _, _, r in panels)
    top = 150
    H = top + ph + 130
    f = Fig(name, "One archaeological reading on two kinds of place", W, H, outdir)
    f.text(50, 40, "The same four statements on a cave and on a findspot, and a findspot without them", 26, True, anchor="start")
    f.text(50, 76, "The properties sit on crm:E27_Site, so both branches use them; their absence is not a negative result.", 19, color=MUTED, anchor="start", maxw=W - 100)
    for i, (title, sub, rows) in enumerate(panels):
        CC.draw_card(f, x0 + i * (pw + gap), top, pw, ph, title, sub, rows, F.OWN_FILL["geolod"])
    f.text(50, H - 62, "Chauvet cave and the CI findspots are read from the committed graphs; every row is a statement of the node above it.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "A property that is missing says that nobody has looked (a different statement from 'looked and found nothing'), which the page counts on the next figure.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"cave": cur(cave), "arch_ci": cur(cia), "plain": cur(plain)}


# ------------------------------------------------------------------ looked at, found, or not looked at

def screening_fig(D: ArchData, outdir: Path, name: str) -> tuple[Fig, dict]:
    # per kind of place: places, screened, typed archaeological, typed archaeological and screened
    rows = [("Caves", D.n_caves, D.cave_screened, D.cave_positive, D.cave_curated), ("CI findspots", D.n_ci, D.ci_screened, D.ci_positive, D.ci_curated)]
    left, right, top, rowh = 300, 1650, 190, 150
    W, H = 1750, top + rowh * len(rows) + 210
    f = Fig(name, "Looked at, found, not looked at", W, H, outdir)
    f.text(50, 40, "Where the graph says nothing, nobody has looked", 26, True, anchor="start")
    f.text(50, 76, "geolod:screenedForArchaeology and the archaeological classes, counted per kind of place.", 19, color=MUTED, anchor="start")
    scale = (right - left) / D.n_caves
    for i, (lab, n, scr, pos, cur_) in enumerate(rows):
        y = top + i * rowh
        f.text(left - 20, y + 40, lab, 24, True, anchor="end")
        f.text(left - 20, y + 72, f"{n} places", 17, color=MUTED, anchor="end")
        parts = [(cur_, EVIDENCE, f"{cur_} with evidence, read"), (pos - cur_, TYPED_ONLY, f"{pos - cur_} typed, not read"),
                 (scr - cur_, SCREENED, f"{scr - cur_} screened, no evidence"), (n - scr - (pos - cur_), SILENT, f"{n - scr - (pos - cur_)} no statement")]
        x = left
        for cnt, colour, text in parts:
            w = round(cnt * scale, 1)
            if cnt:
                f.rect(x, y + 14, w, 52, colour, BLACK, 0, 1)
                label = text if tw(text, 17) + 16 < w else (str(cnt) if tw(str(cnt), 17) + 10 < w else "")
                if label:
                    f.text(x + w / 2, y + 40, label, 17, True, "#ffffff" if colour == EVIDENCE else INK, maxw=w - 6)
                else:
                    f.line(x + w / 2, y + 66, x + w / 2 + 30, y + 100, None, w=.8, color=MUTED)
                    f.text(x + w / 2 + 36, y + 102, text, 17, color=INK, anchor="start")
            x += w
    ly = top + rowh * len(rows) + 40
    xx = left
    for colour, text in ((EVIDENCE, "archaeological class and a curated reading"), (TYPED_ONLY, "archaeological class, no curated reading"),
                         (SCREENED, "screened, no evidence"), (SILENT, "no statement")):
        f.rect(xx, ly - 11, 22, 22, colour, BLACK, 3)
        f.text(xx + 32, ly, text, 18, color=MUTED, anchor="start")
        xx += 32 + tw(text, 18) + 34
    f.text(50, H - 62, f"All {D.cave_positive} archaeological caves carry a curated reading. Of the {D.ci_positive} findspots typed as archaeological, {D.ci_curated} do; the other {D.ci_positive - D.ci_curated} come from the findspot source alone.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "Absence of screenedForArchaeology is kept distinguishable from a negative result (the comment of the property); the bars do not count the silent places as negative.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"caves": (D.n_caves, D.cave_screened, D.cave_positive, D.cave_curated), "ci": (D.n_ci, D.ci_screened, D.ci_positive, D.ci_curated)}


# ------------------------------------------------------------------ context and confidence

def context_fig(D: ArchData, outdir: Path, name: str) -> tuple[Fig, dict]:
    ctxs = [c for c in CONTEXT_ORDER if any(k[1] == c for k in D.contexts)]
    extra = sorted({k[1] for k in D.contexts} - set(CONTEXT_ORDER))
    ctxs += extra
    left, barw, top, rowh = 360, 900, 170, 70
    W, H = 1750, top + rowh * len(ctxs) + 190
    f = Fig(name, "Archaeological sites by broader context and confidence", W, H, outdir)
    f.text(50, 40, "What the archaeological sites are known for, and how sure the attribution is", 26, True, anchor="start")
    f.text(50, 76, f"geolod:archaeologicalBroaderContext (a controlled geolod:ArchaeologicalContext) and geolod:archaeologicalConfidence of the {sum(D.contexts.values())} sites.", 19, color=MUTED, anchor="start", maxw=W - 100)
    mx = max(sum(v for k, v in D.contexts.items() if k[1] == c) for c in ctxs)
    unit = barw / (mx + 2)
    for t in range(0, mx + 3, 5):
        x = left + t * unit
        f.line(x, top - 14, x, top + rowh * len(ctxs) - 14, None, w=1, color=GRID)
        f.text(x, top - 30, str(t), 16, color=MUTED)
    for i, c in enumerate(ctxs):
        y = top + i * rowh
        f.text(left - 18, y + rowh / 2, c.replace("Context", ""), 20, True, anchor="end")
        x = left
        total = 0
        for conf, colour in CONFIDENCE:
            n = sum(v for k, v in D.contexts.items() if k[1] == c and k[2] == conf)
            total += n
            if n:
                w = round(n * unit, 1)
                f.rect(x, y + 12, w, rowh - 30, colour, BLACK, 0, 1)
                if w > 26:
                    f.text(x + w / 2, y + rowh / 2 - 3, str(n), 17, True, "#ffffff" if conf == "high" else INK)
                x += w
        ci_n = sum(v for k, v in D.contexts.items() if k[0] == "CI" and k[1] == c)
        f.text(x + 14, y + rowh / 2 - 3, f"{total}" + (f"  ({ci_n} of them findspots)" if ci_n else ""), 18, anchor="start")
    ly = top + rowh * len(ctxs) + 30
    for xx, (conf, colour) in zip((left, left + 220, left + 460), CONFIDENCE):
        f.rect(xx, ly - 11, 22, 22, colour, BLACK, 3)
        f.text(xx + 32, ly, f"confidence {conf}", 18, color=MUTED, anchor="start")
    f.text(50, H - 62, f"{sum(D.contexts.values())} sites in {len(ctxs)} contexts: {D.cave_curated} caves and {D.ci_curated} CI findspots with a curated reading.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "The category beside the context (for example 'Palaeolithic Art') stays free text; only the broader context is a controlled term.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"rows": {f"{k[0]}/{k[1]}/{k[2]}": v for k, v in sorted(D.contexts.items())}, "total": sum(D.contexts.values())}



# ------------------------------------------------------------------ one eruption, several published ages

TIME = Namespace("http://www.w3.org/2006/time#")
ERUPTION_SPAN = G["ci_eruption_timespan"]
# colours: the age adopted for the event, a competing age of the eruption, the age of the tephra layer in one core
AGE_ADOPTED, AGE_COMPETING, AGE_LAYER = "#0072B2", "#56B4E9", "#E69F00"


def eruption_ages(D: ArchData) -> list[dict]:
    """The published ages of the CI eruption, read from the dating assertions on its time-span."""
    ci = D.ci
    adopted = set(ci.objects(ERUPTION_SPAN, G.hasTimePosition))
    rows = []
    for a in ci.subjects(CRM.P140_assigned_attribute_to, ERUPTION_SPAN):
        tp = ci.value(a, CRM.P141_assigned)
        trs = _local(ci.value(tp, TIME.hasTRS))
        cite = str(ci.value(a, DCTERMS.bibliographicCitation))
        m = re.match(r"([^,]+),.*\((\d{4})\)", cite)
        if not m:
            raise ValueError(f"{a}: no author and year in the citation: {cite!r}")
        published = str(ci.value(tp, SKOS.note)).removeprefix("Published as ").rstrip(".")
        unc_node = ci.value(tp, G.hasAgeUncertainty)
        if unc_node is None:
            raise ValueError(f"{tp}: no geolod:hasAgeUncertainty node; rebuild CI/rdf with CI/ci_pipeline.py")
        cov = ci.value(unc_node, G.coverageLevel)
        iv = ci.value(unc_node, G.hasAgeInterval)
        older = float(ci.value(ci.value(ci.value(iv, TIME.hasBeginning), TIME.inTimePosition), TIME.numericPosition))
        younger = float(ci.value(ci.value(ci.value(iv, TIME.hasEnd), TIME.inTimePosition), TIME.numericPosition))
        rows.append({"cov": float(cov) if cov is not None else None, "older": older, "younger": younger,
                     "who": f"{m.group(1)} et al. {m.group(2)}", "ka": float(ci.value(tp, TIME.numericPosition)),
                     "unc": float(ci.value(tp, G.ageUncertaintyPos_ka)), "trs": trs, "published": published,
                     "adopted": tp in adopted, "layer": trs.startswith("ELSA")})
    if len(rows) < 2:
        raise ValueError("the committed CI graph holds fewer than two dating assertions on the eruption time-span")
    return sorted(rows, key=lambda r: -r["ka"])


def eruption_fig(D: ArchData, outdir: Path, name: str) -> tuple[Fig, dict]:
    """The eruption as the root of the CI strand: its place, its findspots, and its time-span with every published age.

    Each age is a CRM attribute assignment that points at a time position; the time position is drawn as the bar
    (value and uncertainty on one ka axis) and names its own reference system.
    """
    from build import chip, CLS, INST, TERM
    ci = D.ci
    ev = G["ci_volcanic_event"]
    place = ci.value(ev, CRM.P7_took_place_at)
    wd = ci.value(place, SKOS.closeMatch)
    sites = set(ci.objects(ev, CRM.P12_occurred_in_the_presence_of))
    arch = {x for x in sites if (x, RDF.type, G.CIArchaeologicalSite) in ci}
    if place is None or wd is None or not sites:
        raise ValueError("the committed CI graph holds no source area or no findspots on the eruption")
    qid = str(wd).rsplit("/", 1)[-1]
    rows = eruption_ages(D)
    for r in rows:
        r["doi"] = None
    for a_ in ci.subjects(CRM.P140_assigned_attribute_to, ERUPTION_SPAN):
        tp = ci.value(a_, CRM.P141_assigned)
        for r in rows:
            if r["trs"] == _local(ci.value(tp, TIME.hasTRS)):
                r["doi"] = str(ci.value(a_, PROV.wasDerivedFrom)).replace("https://doi.org/", "doi:")
    lo, hi = min(r["ka"] - r["unc"] for r in rows), max(r["ka"] + r["unc"] for r in rows)
    a0, a1 = math.floor((lo - 0.1) * 5) / 5, math.ceil((hi + 0.1) * 5) / 5
    W, rowh, top = 2250, 270, 330
    H = top + rowh * (len(rows) - 1) + 330
    f = Fig(name, "The Campanian Ignimbrite eruption as the root of the CI strand", W, H, outdir)
    cy = top + rowh * (len(rows) - 1) / 2
    # root, and its three branches
    rx0, rw, cx1, cw = 30, 270, 620, 320
    f.box(rx0, cy - 100, rw, 200, "CI eruption", "crm:E5_Event, strat:Eruption", INST, 30, 17)
    f.box(cx1, 70, cw, 110, "Phlegraean Fields", f"crm:E53_Place, wd:{qid}", INST, 24, 17)
    f.box(cx1, cy - 55, cw, 110, "Time-span", "crm:E52_Time-Span", INST, 24, 18)
    f.box(cx1, H - 190, cw, 120, "Findspots (selection)", f"{len(sites)} crm:E27_Site, {len(arch)} also CRMarchaeo A2", INST, 24, 17)
    for (tx, ty, txt) in ((cx1, 125, "P7 took place at"), (cx1, cy, "P4 has time-span"), (cx1, H - 130, "P12 occurred in the presence of")):
        f.line(rx0 + rw, cy, tx - 2, ty, None if False else "a")
        chip(f, (rx0 + rw + tx) / 2, (cy + ty) / 2, txt, 15)
    # one assertion per published age
    ex, ew, px, pw, ph = 1250, 280, 1700, 520, 130
    inner0, inner1 = px + 30, px + pw - 30
    x_of = lambda v: inner0 + (v - a0) / (a1 - a0) * (inner1 - inner0)
    t = a0
    while t <= a1 + 1e-9:
        f.text(x_of(t), top - ph / 2 - 26, f"{t:.1f}", 16, color=MUTED)
        t += 0.2
    f.text(px + pw, top - ph / 2 - 58, "ka BP", 16, True, color=MUTED, anchor="end")
    for i, r in enumerate(rows):
        y = top + i * rowh
        colour = AGE_ADOPTED if r["adopted"] else AGE_LAYER if r["layer"] else AGE_COMPETING
        f.box(ex, y - 50, ew, 100, r["who"], "crm:E13_Attribute_Assignment", CLS, 22, 15)
        f.text(ex + ew / 2, y + 74, f"source: {r['doi']}", 15, color=MUTED)
        f.line(ex, y, cx1 + cw + 2, cy, "a")
        chip(f, (ex + cx1 + cw) / 2, (y + cy) / 2, "P140 assigned attribute to", 15)
        f.line(ex + ew, y, px - 2, y, "a")
        chip(f, (ex + ew + px) / 2, y, "P141 assigned", 15)
        # the time position, drawn as its own bar
        f.rect(px, y - ph / 2, pw, ph, "#ffffff", "#000000", 6, 1)
        f.text(px + 16, y - ph / 2 + 24, f"{r['ka']:.2f} \u00b1 {r['unc']:.2f} ka", 21, True, anchor="start")
        f.text(px + pw - 16, y - ph / 2 + 24, "time:TimePosition", 15, color=MUTED, anchor="end")
        tt = a0
        while tt <= a1 + 1e-9:
            f.line(x_of(tt), y - 8, x_of(tt), y + ph / 2 - 8, None, w=1, color=GRID)
            tt += 0.2
        by = y + 24
        f.line(x_of(r["ka"] - r["unc"]), by, x_of(r["ka"] + r["unc"]), by, None, w=6, color=colour)
        for v in (r["ka"] - r["unc"], r["ka"] + r["unc"]):
            f.line(x_of(v), by - 13, x_of(v), by + 13, None, w=3, color=colour)
        f.raw(f'<circle cx="{x_of(r["ka"]):.1f}" cy="{by}" r="10" fill="{colour}" stroke="#000000" stroke-width="1.5"/>')
        f.line(px + pw / 2, y + ph / 2, px + pw / 2, y + ph / 2 + 56, "a")
        chip(f, px + pw / 2, y + ph / 2 + 28, "time:hasTRS", 15)
        f.box(px + 80, y + ph / 2 + 58, pw - 160, 46, f"trs:{r['trs']}", None, TERM, 17)
    f.legend(H - 28, [(INST, "instance"), (CLS, "class of the assignment"), (TERM, "time reference system"),
                      ((AGE_ADOPTED,), "adopted age of the event"), ((AGE_COMPETING,), "competing age of the eruption"),
                      ((AGE_LAYER,), "age of the tephra layer in one core, not of the vent")], x=50)
    f.save()
    return f, {"rows": {r["trs"]: (r["ka"], r["unc"]) for r in rows}, "sites": len(sites), "arch": len(arch)}


# ------------------------------------------------------------------ the map

def map_fig(D: ArchData, outdir: Path, name: str, pad: float = 4.0) -> tuple[Fig, dict]:
    lons, lats = [p[1] for p in D.findspots], [p[2] for p in D.findspots]
    bbox = (min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad)
    import math
    k = math.cos(math.radians((bbox[1] + bbox[3]) / 2))
    left, top, mapw = 70, 140, 1500
    maph = round(mapw * (bbox[3] - bbox[1]) / ((bbox[2] - bbox[0]) * k))
    W, H = 1750, top + maph + 170
    f = Fig(name, "Campanian Ignimbrite findspots and archaeological caves", W, H, outdir)
    f.text(50, 40, "Where the Campanian Ignimbrite was found, and which caves have archaeology", 26, True, anchor="start")
    f.text(50, 76, "geolod:CIFindspot by the certainty of its position, geolod:CIArchaeologicalSite ringed, geolod:ArchaeologicalCaveSite as diamonds.", 19, color=MUTED, anchor="start", maxw=W - 100)
    X = lambda lon: round(left + (lon - bbox[0]) / (bbox[2] - bbox[0]) * mapw, 1)
    Y = lambda lat: round(top + (bbox[3] - lat) / (bbox[3] - bbox[1]) * maph, 1)
    f.rect(left, top, mapw, maph, "#eef3f7", "#bdbbb2", 0, 1)
    tol = (bbox[2] - bbox[0]) / mapw * 0.6
    land = []
    for ring in BM._rings_of(BM.land_path(str(D.repo))):
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        if max(xs) < bbox[0] or min(xs) > bbox[2] or max(ys) < bbox[1] or min(ys) > bbox[3]:
            continue
        cut = BM.simplify(BM.clip_ring(ring, bbox), tol)
        if len(cut) >= 3:
            land.append("M" + " L".join(f"{X(x)} {Y(y)}" for x, y in cut) + "Z")
    f.raw(f'<path d="{" ".join(land)}" fill="#f4f1e6" stroke="#b9b6a8" stroke-width=".8" stroke-linejoin="round"/>')
    for lon in range(math.ceil(bbox[0] / 10) * 10, int(bbox[2]) + 1, 10):
        f.line(X(lon), top, X(lon), top + maph, None, w=.6, color="#d6dde2")
        f.text(X(lon), top + maph + 18, f"{lon}°E", 15, color=MUTED)
    for lat in range(math.ceil(bbox[1] / 10) * 10, int(bbox[3]) + 1, 10):
        f.line(left, Y(lat), left + mapw, Y(lat), None, w=.6, color="#d6dde2")
        f.text(left - 10, Y(lat), f"{lat}°N", 15, color=MUTED, anchor="end")
    for local, lon, lat, level, arch, cur_ in D.findspots:
        f.raw(f'<circle cx="{X(lon)}" cy="{Y(lat)}" r="6" fill="{LEVEL_COLOUR[level]}" stroke="{BLACK}" stroke-width=".7"/>')
    for local, lon, lat, level, arch, cur_ in D.findspots:
        if arch:
            f.raw(f'<circle cx="{X(lon)}" cy="{Y(lat)}" r="12" fill="none" stroke="{BLACK}" stroke-width="2"/>')
        if cur_:
            f.raw(f'<circle cx="{X(lon)}" cy="{Y(lat)}" r="17" fill="none" stroke="{BLACK}" stroke-width="1.2"/>')
    inside = [c for c in D.arch_caves if bbox[0] <= c[2] <= bbox[2] and bbox[1] <= c[3] <= bbox[3]]
    for _, _, lon, lat in inside:
        x, y = X(lon), Y(lat)
        f.raw(f'<path d="M{x} {y - 8} L{x + 8} {y} L{x} {y + 8} L{x - 8} {y} Z" fill="#ffffff" stroke="{BLACK}" stroke-width="1.6"/>')
    # legend
    ly = top + maph + 52
    xx = left
    for level in LEVEL_ORDER:
        n = sum(1 for p in D.findspots if p[3] == level)
        if not n:
            continue
        f.raw(f'<circle cx="{xx + 8}" cy="{ly}" r="6" fill="{LEVEL_COLOUR[level]}" stroke="{BLACK}" stroke-width=".7"/>')
        text = f"{level} · {n}"
        f.text(xx + 22, ly, text, 17, color=MUTED, anchor="start")
        xx += 36 + tw(text, 17) + 20
    f.raw(f'<circle cx="{xx + 12}" cy="{ly}" r="12" fill="none" stroke="{BLACK}" stroke-width="2"/>')
    f.text(xx + 32, ly, f"archaeological site · {D.ci_positive}", 17, color=MUTED, anchor="start")
    xx += 40 + tw(f"archaeological site · {D.ci_positive}", 17) + 22
    f.raw(f'<circle cx="{xx + 12}" cy="{ly}" r="12" fill="none" stroke="{BLACK}" stroke-width="2"/><circle cx="{xx + 12}" cy="{ly}" r="17" fill="none" stroke="{BLACK}" stroke-width="1.2"/>')
    f.text(xx + 38, ly, f"with a curated reading · {D.ci_curated}", 17, color=MUTED, anchor="start")
    xx += 46 + tw(f"with a curated reading · {D.ci_curated}", 17) + 28
    f.raw(f'<path d="M{xx + 8} {ly - 8} L{xx + 16} {ly} L{xx + 8} {ly + 8} L{xx} {ly} Z" fill="#ffffff" stroke="{BLACK}" stroke-width="1.6"/>')
    f.text(xx + 26, ly, f"archaeological cave in the window · {len(inside)}", 17, color=MUTED, anchor="start")
    f.text(50, H - 62, f"{len(D.findspots)} findspots; the fill is the geolod:hasCertaintyLevel of the geometry node, so the certainty belongs to the position, not to the place.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, f"{len(inside)} of the {len(D.arch_caves)} archaeological caves lie in this window; the others lie outside it.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"findspots": sorted((a, round(b, 4), round(c, 4), d) for a, b, c, d, _, _ in D.findspots), "caves": sorted((a, round(c, 4), round(d, 4)) for a, _, c, d in D.arch_caves),
               "inside": len(inside), "bbox": bbox}
