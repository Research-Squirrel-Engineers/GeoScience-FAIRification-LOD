"""Figures of the cluster page "Sources and provenance".

The data come from the committed graphs: the EPICA graph (the catalogue, five datasets, five sources, 4 904 observations),
the MIS vocabulary (two sources), the SISAL catalogue with its annotations, the SISAL dating points and the CI findspots
with their annotations, together with the ontology files that define the classes. Every number printed on a figure is
counted from there; nothing is typed in.

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS

import cluster_cards as CC
import model_data as md
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
G = Namespace("http://w3id.org/geo-lod/")
EPICA = Namespace("http://w3id.org/geo-lod/epica/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
BLACK, GRID, INK = "#000000", "#d8d6ce", "#1f1f1d"
TYPED, UNTYPED = "#0072B2", "#E69F00"
FILES = ["EPICA/rdf/epica_dome_c.ttl", "ontology/vocab/mis.ttl", "SISAL/rdf/sisal_sites.ttl", "SISAL/rdf/sisal_site_annotations.ttl",
         "SISAL/rdf/sisal_v3_dating.ttl", "CI/rdf/ci_findspots.ttl", "CI/rdf/ci_site_annotations.ttl",
         "ontology/geo_lod_core.ttl", "EPICA/rdf/epica_ontology.ttl", "SISAL/rdf/sisal_ontology.ttl"]
EXAMPLE = "ch4"


def _local(iri) -> str:
    return str(iri).rsplit("/", 1)[-1]


def licence_short(iri) -> str:
    m = re.search(r"licenses/([a-z-]+)/(\d\.\d)", str(iri))
    return f"CC {m.group(1).upper()} {m.group(2)}" if m else str(iri)


class SrcData:
    """All the committed graphs in one graph `g`; the sources and what derives from them are read once."""

    def __init__(self, repo: Path = REPO):
        g = Graph()
        for rel in FILES:
            for t in Graph().parse(repo / rel, format="turtle"):
                g.add(t)
        for pfx, ns in (("geolod", G), ("epica", EPICA), ("dcat", DCAT), ("prov", PROV), ("dct", DCTERMS), ("rdfs", RDFS), ("owl", OWL)):
            g.bind(pfx, ns)
        self.g, self.repo = g, repo
        typed = set(g.subjects(RDF.type, G.DataSource))
        self.typed = sorted(typed)
        self.catalogues = sorted(g.subjects(RDF.type, G.PalaeoclimateDataCatalogue))
        # what derives from a source: the node cites it with prov:wasDerivedFrom or dct:source, and the source is a typed
        # geolod:DataSource or a node the graph says nothing else about (a source the committed Turtle only cites)
        derived: dict[URIRef, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        for pred in (PROV.wasDerivedFrom, DCTERMS.source):
            for x, src in g.subject_objects(pred):
                if not isinstance(src, URIRef) or x in typed:
                    continue
                if src not in typed and any(True for _ in g.predicate_objects(src)):
                    continue
                for cls in g.objects(x, RDF.type):
                    if str(cls).startswith(str(G)):
                        derived[src][_local(cls)].add(x)
        self.derived = {s: {c: len(xs) for c, xs in d.items()} for s, d in derived.items()}
        self.sources = []
        for s in sorted(self.derived, key=lambda u: (u not in typed, str(u))):
            is_typed = s in typed
            lab = min(g.objects(s, RDFS.label), key=str, default=None)
            lic = min(g.objects(s, DCTERMS.license), key=str, default=None)
            date = min(g.objects(s, DCTERMS.date), key=str, default=None)
            self.sources.append({"iri": s, "local": _local(s), "typed": is_typed, "label": str(lab) if lab else _local(s),
                                 "licence": licence_short(lic) if lic else "none stated", "year": str(date) if date else "none",
                                 "classes": sorted(self.derived[s].items(), key=lambda kv: (-kv[1], kv[0]))})
        if not self.sources:
            raise ValueError("the committed graphs cite no sources; the figures have nothing to draw")


# ------------------------------------------------------------------ catalogue, dataset, source

def pattern_fig(M: md.Model, D: SrcData, outdir: Path, name: str) -> tuple[Fig, dict]:
    g = D.g
    nm = g.namespace_manager
    cur = lambda t: t.n3(nm)
    cat = D.catalogues[0]
    ds = EPICA[f"dataset_{EXAMPLE}"]
    src = g.value(ds, DCTERMS.source)
    if src is None or (src, RDF.type, G.DataSource) not in g:
        raise ValueError(f"{name}: {ds} has no typed source")
    obs = sorted(g.objects(ds, G.hasObservation))
    cited = sorted(g.subjects(PROV.wasDerivedFrom, src))
    n_ds = len(set(g.objects(cat, DCAT.dataset)))
    if ds not in set(g.objects(cat, DCAT.dataset)):
        raise ValueError(f"{name}: the catalogue does not list {ds}")

    def count_row(label, text):
        return (label, "lit", text, "")

    cat_rows = [CC.card_row(g, cat, DCTERMS.title, "lit"), CC.card_row(g, cat, DCTERMS.publisher, "lit"), CC.card_row(g, cat, DCTERMS.created, "lit"),
                ("dcat:dataset", "node", cur(ds), CC.node_class(g, ds, nm)), count_row("datasets in the catalogue", str(n_ds))]
    ds_rows = [CC.card_row(g, ds, DCTERMS.title, "lit"), CC.card_row(g, ds, DCTERMS.license, "lit"),
               ("dct:source", "node", cur(src), CC.node_class(g, src, nm)), ("geolod:hasObservation", "node", cur(obs[0]), CC.node_class(g, obs[0], nm)),
               count_row("observations of the dataset", f"{len(obs):,}")]
    src_rows = [CC.card_row(g, src, RDFS.label, "lit"), CC.card_row(g, src, DCTERMS.creator, "lit"), CC.card_row(g, src, DCTERMS.date, "lit"),
                CC.card_row(g, src, DCTERMS.license, "lit"), CC.card_row(g, src, DCTERMS.source, "lit"),
                count_row("observations citing it", f"{len(cited):,}")]
    for rows in (cat_rows, ds_rows, src_rows):                       # the licence IRIs are long; say what they are
        for i, r in enumerate(rows):
            if r[0] in ("dct:license",):
                rows[i] = (r[0], "lit", licence_short(r[2].strip("<>")), "")
    panels = [(f"The catalogue: {cur(cat)}", "geolod:PalaeoclimateDataCatalogue and dcat:Catalog", cat_rows),
              (f"A dataset: {cur(ds)}", "geolod:IceCoreDataset, a dcat:Dataset and a prov:Entity", ds_rows),
              (f"A source: {cur(src)}", "geolod:DataSource, a crm:E73 and a prov:Entity", src_rows)]
    W, pw, gap, x0 = 1900, 590, 30, 50
    ph = max(CC.card_height(r) for _, _, r in panels)
    top = 150
    H = top + ph + 130
    f = Fig(name, "From a catalogue to a source", W, H, outdir)
    f.text(50, 40, "Catalogue, dataset, source: three nodes, and every observation points to the third", 26, True, anchor="start")
    f.text(50, 76, "The EPICA methane record, every row read from the committed graph; a dataset names its source, and so does each of its observations.", 19, color=MUTED, anchor="start", maxw=W - 100)
    for i, (title, sub, rows) in enumerate(panels):
        CC.draw_card(f, x0 + i * (pw + gap), top, pw, ph, title, sub, rows, F.OWN_FILL["geolod"])
    f.text(50, H - 62, "The dataset names its source with dct:source, each observation with prov:wasDerivedFrom: the same source at two levels, so a reader can start from either.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "The licence is a property of the source and of the dataset; the observations carry none of their own.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"catalogue": cur(cat), "datasets": n_ds, "dataset": cur(ds), "source": cur(src), "observations": len(obs), "cited": len(cited)}


# ------------------------------------------------------------------ who cites which source

def sources_fig(D: SrcData, outdir: Path, name: str) -> tuple[Fig, dict]:
    rows = D.sources
    left, top, rowh = 60, 200, 70
    cx = [640, 980, 1130, 1260]
    W, H = 1900, top + rowh * len(rows) + 190
    f = Fig(name, "Which sources the graphs cite", W, H, outdir)
    f.text(50, 40, "Every source the graphs cite, what derives from it, and whether it has a node here", 26, True, anchor="start")
    f.text(50, 76, "Nodes with prov:wasDerivedFrom or dct:source, counted by class; a source is typed (geolod:DataSource) or only cited.", 19, color=MUTED, anchor="start", maxw=W - 100)
    for x, t in zip([left] + cx, ["Source", "node here", "licence", "year", "nodes derived from it, by class"]):
        f.text(x, top - 36, t, 17, True, anchor="start")
    for i, s in enumerate(rows):
        y = top + i * rowh
        if i % 2 == 0:
            f.rect(50, y, W - 100, rowh, "#f6f6f3")
        f.text(left, y + rowh / 2 - 12, F.fit(s["label"], 19, 540, True), 19, True, anchor="start")
        f.text(left, y + rowh / 2 + 14, s["local"], 15, color=MUTED, anchor="start", maxw=540)
        f.rect(cx[0], y + 17, 160, rowh - 34, TYPED if s["typed"] else "#ffffff", BLACK if s["typed"] else UNTYPED, 5, 2 if not s["typed"] else 1)
        f.text(cx[0] + 80, y + rowh / 2, "typed" if s["typed"] else "cited only", 17, True, "#ffffff" if s["typed"] else INK)
        f.text(cx[1], y + rowh / 2, s["licence"], 18, anchor="start", color=INK if s["licence"] != "none stated" else "#9a988f", maxw=140)
        f.text(cx[2], y + rowh / 2, s["year"], 18, anchor="start", color=INK if s["year"] != "none" else "#9a988f")
        parts = [f"{n:,} {c}" for c, n in s["classes"][:2]] + ([f"+ {len(s['classes']) - 2} more classes"] if len(s["classes"]) > 2 else [])
        f.text(cx[3], y + rowh / 2, F.fit("  ·  ".join(parts), 18, W - cx[3] - 70), 18, anchor="start")
    n_typed = sum(1 for s in rows if s["typed"])
    f.text(50, H - 62, f"{len(rows)} sources: {n_typed} typed as geolod:DataSource in the committed graphs, {len(rows) - n_typed} cited by IRI only.", 17, color=MUTED, anchor="start", maxw=W - 100)
    names = ", ".join(s["local"] for s in rows if not s["typed"]) or "none"
    f.text(50, H - 32, f"No node of their own in the committed Turtle: {names}. The SISAL one is defined by the pipeline in its large graph.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"rows": {s["local"]: (s["typed"], tuple(s["classes"])) for s in rows}, "typed": n_typed, "cited": len(rows) - n_typed}
