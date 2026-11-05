"""Figures of the cluster page "Archives and sampling".

The data come from the committed graphs: `EPICA/rdf/epica_dome_c.ttl` (site, boreholes, campaign, core, datasets, the
814 sections of the deuterium record) and `SISAL/rdf/sisal_sites.ttl` (365 caves with their sample counts), together with
the three ontology files that define the classes. The SISAL speleothems and samples belong to the large graph the
pipeline writes; the pattern figure draws them from the SISAL tables with the IRIs and properties of `sisal_rdf.py` and
says so. Every number printed on a figure is counted from the graphs; nothing is typed in.

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS

import model_data as md
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
G = Namespace("http://w3id.org/geo-lod/")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
SF = Namespace("http://www.opengis.net/ont/sf#")
BLACK, GRID, INK = "#000000", "#d8d6ce", "#1f1f1d"
CORE_COLOUR, SECTION_COLOUR = "#0072B2", "#E69F00"        # Okabe-Ito


class ArcData:
    """The EPICA graph, the SISAL cave catalogue and the ontology files in one graph `g` for the queries."""

    def __init__(self, repo: Path = REPO):
        epica = Graph().parse(repo / "EPICA/rdf/epica_dome_c.ttl", format="turtle")
        sites = Graph().parse(repo / "SISAL/rdf/sisal_sites.ttl", format="turtle")
        g = Graph()
        for src in (epica, sites):
            for t in src:
                g.add(t)
        for rel in ("ontology/geo_lod_core.ttl", "EPICA/rdf/epica_ontology.ttl", "SISAL/rdf/sisal_ontology.ttl"):
            for t in Graph().parse(repo / rel, format="turtle"):
                g.add(t)
        for pfx, ns in (("geolod", G), ("sosa", SOSA), ("crm", CRM), ("rdfs", RDFS), ("dct", DCTERMS)):
            g.bind(pfx, ns)
        self.g, self.epica, self.sites, self.repo = g, epica, sites, repo

        # IceCoreDataset: title, observations by the class of their feature of interest
        self.datasets: list[tuple[str, str, int, int]] = []      # (iri local, title, on the core, on a section)
        for ds in sorted(epica.subjects(RDF.type, G.IceCoreDataset)):
            cnt = {"IceCore": 0, "SampleSection": 0}
            for obs in epica.objects(ds, G.hasObservation):
                for foi in epica.objects(obs, SOSA.hasFeatureOfInterest):
                    for k in cnt:
                        if (foi, RDF.type, G[k]) in epica:
                            cnt[k] += 1
            self.datasets.append((str(ds).rsplit("/", 1)[1], str(next(epica.objects(ds, DCTERMS.title))), cnt["IceCore"], cnt["SampleSection"]))
        # SampleSection: depth intervals
        self.sections = sorted((float(next(epica.objects(s, G.depthTop_m))), float(next(epica.objects(s, G.depthBottom_m))))
                               for s in epica.subjects(RDF.type, G.SampleSection))
        # Caves: label and the number of delta-18-O samples counted on them
        self.caves = sorted(((str(next(sites.objects(c, RDFS.label))), int(next(sites.objects(c, G.countD18OSamples))))
                             for c in sites.subjects(RDF.type, G.Cave)), key=lambda x: (-x[1], x[0]))
        if not self.datasets or not self.sections or not self.caves:
            raise ValueError("the archive graphs hold no datasets, sections or caves; the figures have nothing to draw")


def _rows(path: Path):
    with open(path, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


# ------------------------------------------------------------------ the pattern

def archive_pattern_fig(M: md.Model, D: ArcData, outdir: Path, name: str, entity: str = "55") -> tuple[Fig, dict]:
    """The chain from a place to a measured thing, once for the ice core (nodes of the graph) and once for a speleothem."""
    by = {c.curie: c for c in M.classes.values()}
    need = ["geolod:DrillingCampaign", "geolod:IceCore", "geolod:DrillingSite", "geolod:Borehole", "geolod:SampleSection",
            "geolod:Cave", "geolod:Speleothem", "geolod:SpeleothemSample", "geolod:EntityStatus", "geolod:IceCoreDataset"]
    for n in need:
        if n not in by:
            raise ValueError(f"{name}: {n} is not a class of the ontology")
    anc = {n: M.curie(M.anchors(by[n].iri)[0][0]).split("_")[0] for n in need}
    g, nm = D.epica, D.epica.namespace_manager
    one = lambda t, cls: next(s for s in sorted(g.subjects(RDF.type, G[cls])) if str(s).rsplit("/", 1)[1] == t)
    campaign, core, site = one("campaign_1996_2004", "DrillingCampaign"), one("core_edc", "IceCore"), one("site_dome_c", "DrillingSite")
    borehole, section = one("borehole_domec", "Borehole"), one("sample_dd_0001", "SampleSection")
    obs = next(o for o in sorted(g.subjects(SOSA.hasFeatureOfInterest, section)))
    dataset = next(s for s in sorted(g.subjects(G.hasObservation, obs)))
    # the edges are read, not assumed
    edges = [(campaign, G.removedSample, core), (campaign, G.tookPlaceAt, site), (core, G.extractedFrom, site), (borehole, CRM.P89_falls_within, site),
             (section, CRM.P46i_forms_part_of, core), (obs, SOSA.hasFeatureOfInterest, section), (dataset, G.hasObservation, obs)]
    for s, p, o in edges:
        if (s, p, o) not in g:
            raise ValueError(f"{name}: the graph has no {p} from {s} to {o}")
    cur = lambda t: t.n3(nm)
    top, bot = float(next(g.objects(section, G.depthTop_m))), float(next(g.objects(section, G.depthBottom_m)))

    # SISAL: entity, its cave and one sample, from the tables and the catalogue
    t = D.repo / "data/derived/sisal/tables"
    ent = next(r for r in _rows(t / "entity.csv") if r["entity_id"] == entity)
    cave_iri = f"geolod:Cave_site_{int(ent['site_id']):04d}"
    cave = next(c for c in D.sites.subjects(RDF.type, G.Cave) if str(c).endswith(f"Cave_site_{int(ent['site_id']):04d}"))
    cave_label = str(next(D.sites.objects(cave, RDFS.label)))
    depth = {r["sample_id"]: float(r["depth_sample"]) for r in _rows(t / "sample.csv") if r["entity_id"] == entity}
    sid = sorted(depth, key=lambda k: (depth[k], int(k)))[len(depth) // 2]
    status = ent["entity_status"].replace(", ", "_").replace(" ", "_")

    W, H = 1750, 1240
    f = Fig(name, "From a place to a measured thing", W, H, outdir)
    f.text(50, 40, "A place, a thing taken from it, and the part that was measured: three nodes, not one", 26, True, anchor="start")
    f.text(50, 76, "The site is a place (crm:E27), the core a physical object (crm:E22), the section a part of it (crm:E18); the campaign that removed it is an activity.", 18, color=MUTED, anchor="start", maxw=W - 100)
    gl, own = F.OWN_FILL["geolod"], "#f6f6f3"
    bw, bh = 280, 72

    def node(x, y, title, cls, fill=gl, w=bw):
        f.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{bh}" rx="8" fill="{fill}" stroke="{BLACK}" stroke-width="1.2"/>')
        f.text(x + w / 2, y + bh / 2 - 11, title, 18, True, BLACK, maxw=w - 12)
        f.text(x + w / 2, y + bh / 2 + 15, cls, 14, color="#3a3935", maxw=w - 10)

    def label(cx, cy, text, back=True):
        w = tw(text, 16) + 10
        if back:
            f.rect(round(cx - w / 2, 1), round(cy - 11, 1), round(w, 1), 22, "#ffffff", "none", 4)
        f.text(round(cx, 1), round(cy, 1), text, 16, color=MUTED)

    def harrow(x1, x2, y, text):
        f.line(x1, y, x2, y, "a")
        label((x1 + x2) / 2, y - 18, text, back=False)

    def varrow(x, y1, y2, text):
        f.line(x, y1, x, y2, "a")
        label(x, (y1 + y2) / 2, text)

    c1, c2, c3, c4 = 50, 500, 950, 1400
    r1, r2, r3 = 215, 405, 595
    f.text(50, 132, "The ice core: nodes of EPICA/rdf/epica_dome_c.ttl", 22, True, anchor="start")
    node(c1, r1, cur(campaign), f"geolod:DrillingCampaign · {anc['geolod:DrillingCampaign']}")
    node(c2, r1, cur(core), f"geolod:IceCore · {anc['geolod:IceCore']}")
    node(c3, r1, cur(site), f"geolod:DrillingSite · {anc['geolod:DrillingSite']}")
    node(c4, r1, cur(borehole), f"geolod:Borehole · {anc['geolod:Borehole']}")
    harrow(c1 + bw, c2, r1 + bh / 2, "geolod:removedSample")
    harrow(c2 + bw, c3, r1 + bh / 2, "geolod:extractedFrom")
    harrow(c4, c3 + bw, r1 + bh / 2, "crm:P89_falls_within")
    # the campaign took place at the site: over the core, on a channel above the row
    ytop = r1 - 36
    f.path(f"M{c1 + bw / 2} {r1} L{c1 + bw / 2} {ytop} L{c3 + bw / 2} {ytop} L{c3 + bw / 2} {r1 - 2}", "a")
    label((c1 + c3 + bw) / 2, ytop, "geolod:tookPlaceAt")
    node(c2, r2, cur(section), f"geolod:SampleSection · {anc['geolod:SampleSection']}")
    varrow(c2 + bw / 2, r2, r1 + bh, "crm:P46i_forms_part_of")
    f.text(c3 + 10, r2 + bh / 2 - 12, f"{top:g} to {bot:g} m of the core", 17, color="#9a3412", anchor="start")
    f.text(c3 + 10, r2 + bh / 2 + 14, "an interval the source states", 17, color="#9a3412", anchor="start")
    node(c2, r3, cur(obs), "an observation of the dataset", fill=own)
    varrow(c2 + bw / 2, r3, r2 + bh, "sosa:hasFeatureOfInterest")
    node(c1, r3, cur(dataset), f"geolod:IceCoreDataset · {anc['geolod:IceCoreDataset']}", fill=gl)
    harrow(c1 + bw, c2, r3 + bh / 2, "geolod:hasObservation")
    f.text(c3 + 10, r3 + bh / 2 - 12, "Where the source gives no interval, the observation points", 17, color="#9a3412", anchor="start")
    f.text(c3 + 10, r3 + bh / 2 + 14, f"to the core itself, {cur(core)}.", 17, color="#9a3412", anchor="start")
    f.line(50, r3 + bh + 50, W - 50, r3 + bh + 50, None, w=1.2, color=GRID)

    y0 = r3 + bh + 100
    f.text(50, y0, "The speleothem: entity and sample from the SISAL tables, IRIs and properties as sisal_rdf.py writes them", 22, True, anchor="start")
    s1 = y0 + 60
    node(c1, s1, f"sisal:sample_{int(sid):07d}", f"geolod:SpeleothemSample · {anc['geolod:SpeleothemSample']}")
    node(c2, s1, f"sisal:entity_{int(entity):05d}", f"geolod:Speleothem · {anc['geolod:Speleothem']}")
    node(c3, s1, cave_iri, f"geolod:Cave · {anc['geolod:Cave']}")
    harrow(c1 + bw, c2, s1 + bh / 2, "geolod:collectedFrom")
    harrow(c2 + bw, c3, s1 + bh / 2, "geolod:extractedFrom")
    s2 = s1 + 160
    node(c2, s2, f"geolod:EntityStatus_{status}", f"geolod:EntityStatus · {anc['geolod:EntityStatus']}", fill=own)
    varrow(c2 + bw / 2, s2, s1 + bh, "geolod:entityStatus")
    f.text(c4 - 120, s1 + bh / 2 - 12, f"{cave_label}, speleothem {ent['entity_name']}", 17, color="#9a3412", anchor="start")
    f.text(c4 - 120, s1 + bh / 2 + 14, f"sample taken {depth[sid]:g} mm from the top", 17, color="#9a3412", anchor="start")
    f.text(50, H - 70, "In both chains the place, the thing taken from it and the part measured are three nodes with three CRM anchors; a measurement can then say which of them it is about.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 40, "The speleothem nodes belong to the large graph the pipeline writes; the committed Turtle holds the 365 caves and the dating points only.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"section": cur(section), "core": cur(core), "dataset": cur(dataset)}


# ------------------------------------------------------------------ what the graphs hold per class

def inventory_fig(M: md.Model, clusters_iris: list[str], D: ArcData, rows: dict[str, tuple[int, int]], outdir: Path, name: str,
                  zero_note: str = "0 and 0: the class is used by the pipeline (SISAL speleothems and samples, entity status terms) and its nodes are in the large graph, not in the committed Turtle.") -> Fig:
    """One row per class of the cluster: the CRM anchor, the nodes asserted with that class, the nodes of it or a subclass."""
    items = sorted(clusters_iris, key=M.curie)
    left, top, rowh = 60, 170, 38
    cx = [560, 800, 1060]
    W, H = 1750, top + rowh * len(items) + 130
    f = Fig(name, "What the committed graphs hold per class", W, H, outdir)
    f.text(50, 40, "Which classes have nodes in the committed graphs", 26, True, anchor="start")
    f.text(50, 76, "Asserted: nodes typed with the class itself. With subclasses: nodes typed with it or any class below it (rdfs:subClassOf).", 19, color=MUTED, anchor="start")
    f.text(left, top - 30, "Class", 17, True, anchor="start")
    f.text(cx[0], top - 30, "CRM anchor", 17, True, anchor="start")
    f.text(cx[1] + 90, top - 30, "Asserted", 17, True, anchor="end")
    f.text(cx[2], top - 30, "With subclasses", 17, True, anchor="start")
    mx = max(max(a, b) for a, b in rows.values()) or 1
    for i, iri in enumerate(items):
        y = top + i * rowh
        cur = M.curie(iri)
        a, b = rows.get(cur, (0, 0))
        if i % 2 == 0:
            f.rect(50, y, W - 100, rowh, "#f6f6f3")
        f.text(left, y + rowh / 2, cur, 18, True, anchor="start", maxw=480)
        f.text(cx[0], y + rowh / 2, ", ".join(M.curie(x).split("_")[0] for x in M.anchors(iri)[0]), 17, color=MUTED, anchor="start", maxw=230)
        f.text(cx[1] + 90, y + rowh / 2, str(a) if a else "0", 18, color=INK if a else "#b5b3aa", anchor="end")
        if b:
            w = max(3.0, round(520 * b / mx, 1))
            f.rect(cx[2], y + 8, w, rowh - 16, "#0072B2" if a else "#9a3412", BLACK, 0, 1)
            f.text(cx[2] + w + 10, y + rowh / 2, str(b), 17, anchor="start")
        else:
            f.text(cx[2], y + rowh / 2, "0", 18, color="#b5b3aa", anchor="start")
    f.text(50, H - 60, "Blue: the class has asserted nodes. Orange: the class is only a superclass here, its nodes are typed with a subclass.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, zero_note, 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f


# ------------------------------------------------------------------ what an observation is about

def feature_fig(D: ArcData, outdir: Path, name: str) -> tuple[Fig, dict]:
    rows = sorted(D.datasets, key=lambda r: -(r[2] + r[3]))
    left, barw, top, rowh = 520, 900, 170, 74
    W, H = 1750, top + rowh * len(rows) + 190
    f = Fig(name, "What the observations of each dataset are about", W, H, outdir)
    f.text(50, 40, "An observation is about the core, or about the section the source states", 26, True, anchor="start")
    f.text(50, 76, "sosa:hasFeatureOfInterest of the observations of each geolod:IceCoreDataset, counted by the class of the node it points to.", 19, color=MUTED, anchor="start")
    mx = max(a + b for _, _, a, b in rows)
    for t in range(0, 1501, 500):
        x = left + barw * t / 1500
        f.line(x, top - 14, x, top + rowh * len(rows) - 14, None, w=1, color=GRID)
        f.text(x, top - 30, str(t), 16, color=MUTED)
    for i, (key, title, a, b) in enumerate(rows):
        y = top + i * rowh
        f.text(left - 18, y + rowh / 2 - 12, title.replace("EPICA Dome C - ", ""), 19, True, anchor="end", maxw=left - 40)
        f.text(left - 18, y + rowh / 2 + 12, key, 15, color=MUTED, anchor="end")
        wa, wb = round(barw * a / 1500, 1), round(barw * b / 1500, 1)
        if a:
            f.rect(left, y + 10, wa, rowh - 30, CORE_COLOUR, BLACK, 0, 1)
        if b:
            f.rect(left + wa, y + 10, wb, rowh - 30, SECTION_COLOUR, BLACK, 0, 1)
        f.text(left + wa + wb + 14, y + rowh / 2 - 6, f"{a + b}" + (f"  ·  {b} on sections" if b else "  ·  on the core"), 19, anchor="start")
    ly = top + rowh * len(rows) + 30
    f.rect(left, ly - 11, 22, 22, CORE_COLOUR, BLACK, 3)
    f.text(left + 32, ly, "geolod:IceCore, the observation is about the core", 18, color=MUTED, anchor="start")
    f.rect(left + 500, ly - 11, 22, 22, SECTION_COLOUR, BLACK, 3)
    f.text(left + 532, ly, "geolod:SampleSection, an interval the source states", 18, color=MUTED, anchor="start")
    n_sec = len(D.sections)
    thick = sum(b - t for t, b in D.sections)
    tiles = all(abs(D.sections[i][1] - D.sections[i + 1][0]) < 1e-6 for i in range(n_sec - 1))
    f.text(50, H - 60, f"The {n_sec} sections tile {D.sections[0][0]:g} to {D.sections[-1][1]:g} m of the core ({thick:.1f} m) {'without gap or overlap' if tiles else 'with gaps or overlaps'}; each is {statistics.median(b - t for t, b in D.sections):.2f} m thick.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "A section is minted only where the source states the interval; the other four records give a depth, and their observations stay on the core.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"rows": {k: (a, b) for k, _, a, b in rows}, "sections": n_sec, "thickness": thick, "tiles": tiles,
               "top": D.sections[0][0], "bottom": D.sections[-1][1]}


# ------------------------------------------------------------------ caves

def caves_fig(D: ArcData, outdir: Path, name: str) -> tuple[Fig, dict]:
    ranked = D.caves
    n = len(ranked)
    left, right, top, bottom = 150, 1650, 150, 650
    W, H = 1750, bottom + 150
    f = Fig(name, "How many delta-18-O samples each cave stands for", W, H, outdir)
    f.text(50, 40, "365 caves, and what the graph says about each", 26, True, anchor="start")
    f.text(50, 76, "geolod:countD18OSamples of every geolod:Cave in the catalogue, ranked, on a logarithmic axis.", 19, color=MUTED, anchor="start")
    import math
    lo, hi = 0, math.log10(max(c for _, c in ranked)) + 0.1
    Y = lambda v: round(bottom - (math.log10(max(v, 1)) - lo) / (hi - lo) * (bottom - top), 1)
    X = lambda i: round(left + (right - left) * i / (n - 1), 1)
    for e in range(0, 5):
        v = 10 ** e
        f.line(left, Y(v), right, Y(v), None, w=1, color=GRID)
        f.text(left - 14, Y(v), f"{v:,}", 16, color=MUTED, anchor="end")
    f.text(left - 100, (top + bottom) / 2, "", 16)
    med = statistics.median(c for _, c in ranked)
    f.line(left, Y(med), right, Y(med), None, w=1.8, dash=True, color="#9a3412")
    f.text(right - 8, Y(med) - 14, f"median {med:g}", 17, True, color="#9a3412", anchor="end")
    for i, (lab, c) in enumerate(ranked):
        f.raw(f'<circle cx="{X(i)}" cy="{Y(c)}" r="3.4" fill="#0072B2" stroke="{BLACK}" stroke-width=".6"/>')
    for i in range(3):
        lab, c = ranked[i]
        lx, ly = left + 150, top - 10 + i * 26
        f.line(X(i) + 5, Y(c), lx - 8, ly, None, w=.8, color=MUTED)
        f.text(lx, ly, f"{lab}: {c:,}", 17, anchor="start")
    f.text(left, bottom + 40, "Caves, from the one with most samples to the one with fewest", 17, color=MUTED, anchor="start")
    total = sum(c for _, c in ranked)
    f.text(50, H - 60, f"{n} caves, {total:,} samples in all, {ranked[-1][1]} at least. A geolod:Cave carries the count; the speleothems and their samples are separate nodes.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "The counts are SISAL's own; the committed graph holds the catalogue, and the samples are in the large graph written by the pipeline.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"caves": n, "total": total, "median": med, "max": ranked[0], "min": ranked[-1][1]}
