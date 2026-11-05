"""Figures of the WD1 drill-core log on the page "Archives and sampling".

Table 1 of the WD1 core (Schenk et al. 2026, Quaternary 9, 67; tables CC BY 4.0, Fiona Schenk, data/raw/wd1/Table1.csv) is a
log: one row per layer, with a depth interval and a description. This module shows how such a log becomes RDF in the strat:
module: one strat:StratigraphicUnit per row, the depths as decimals, strat:partOfCore, and strat:meets from each unit to the
one below it. The pipeline does not write WD1 yet, so the instances are built here from the CSV and are illustrative; the
strat: classes come from ontology/strat.ttl. Every number printed on a figure is counted from that graph and compared with
a count made from the CSV.

Layout is deterministic: no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

import cluster_cards as CC
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STRAT = Namespace("http://w3id.org/geo-lod/strat/")
WD1 = Namespace("http://w3id.org/geo-lod/wd1/")       # illustrative: w3id.org/geo-lod is not registered yet
BLACK, INK = "#000000", "#1f1f1d"
TEPHRA, LITHO, PLAIN = "#9a3412", "#e7d3b0", "#cfcdc4"
MARKER = "HBT"


class Wd1Log:
    """The log rows, and the graph they become."""

    def __init__(self, repo: Path = REPO):
        self.rows = []                                   # (top, bottom, text) as Decimal, Decimal, str
        for r in list(csv.reader(open(repo / "data/raw/wd1/Table1.csv", encoding="utf8")))[1:]:
            a, b = (Decimal(v) for v in r[0].split("–"))
            self.rows.append((a, b, r[1]))
        if not self.rows:
            raise ValueError("data/raw/wd1/Table1.csv has no rows")
        g = Graph().parse(repo / "ontology/strat.ttl", format="turtle")
        for pfx, ns in (("strat", STRAT), ("wd1", WD1), ("rdfs", RDFS), ("xsd", XSD)):
            g.bind(pfx, ns)
        core = WD1.WD1
        g.add((core, RDF.type, STRAT.Core))
        g.add((core, RDFS.label, Literal("WD1")))
        self.units = []
        for i, (a, b, t) in enumerate(self.rows):
            name = re.search(r"\((WDT|HBT|GLT|JWT)\)", t)
            u = WD1[f"unit_{name.group(1)}" if name else f"unit_{i + 1:03d}"]
            self.units.append(u)
            tephra = "tephra" in t.lower()
            described = not t.startswith("---")
            g.add((u, RDF.type, STRAT.TephraLayer if tephra else (STRAT.LithologicalUnit if described else STRAT.StratigraphicUnit)))
            if described:
                g.add((u, RDFS.label, Literal(t)))
            g.add((u, STRAT.depthTop, Literal(a, datatype=XSD.decimal)))
            g.add((u, STRAT.depthBottom, Literal(b, datatype=XSD.decimal)))
            g.add((u, STRAT.partOfCore, core))
        self.gaps = 0
        for i in range(len(self.rows) - 1):
            if self.rows[i][1] == self.rows[i + 1][0]:
                g.add((self.units[i], STRAT.meets, self.units[i + 1]))
            else:
                self.gaps += 1
        self.g = g
        self.n_tephra = sum(1 for _, _, t in self.rows if "tephra" in t.lower())
        self.n_plain = sum(1 for _, _, t in self.rows if t.startswith("---"))
        self.marker = next((i for i, (_, _, t) in enumerate(self.rows) if f"({MARKER})" in t), None)
        if self.marker is None or not 0 < self.marker < len(self.rows) - 1:
            raise ValueError(f"the log has no unit {MARKER} with a unit above and below it")


def pattern_fig(D: Wd1Log, outdir: Path, name: str) -> tuple[Fig, dict]:
    g = D.g
    nm = g.namespace_manager
    cur = lambda t: t.n3(nm)

    def card(i, role):
        u = D.units[i]
        sub = cur(next(t for t in g.objects(u, RDF.type)))
        rows = []
        if (u, RDFS.label, None) in g:
            rows.append(CC.card_row(g, u, RDFS.label, "lit"))
        rows += [CC.card_row(g, u, STRAT.depthTop, "lit", " m"), CC.card_row(g, u, STRAT.depthBottom, "lit", " m"),
                 CC.card_row(g, u, STRAT.partOfCore, "node"), CC.card_row(g, u, STRAT.meets, "node")]
        return (f"{role}: {cur(u)}", f"{sub}, a strat:StratigraphicUnit", rows)

    m = D.marker
    panels = [card(m - 1, "The layer above"), card(m, "A tephra layer"), card(m + 1, "The layer below")]
    W, pw, gap, x0 = 1900, 590, 30, 50
    ph = max(CC.card_height(r) for _, _, r in panels)
    top = 150
    H = top + ph + 130
    f = Fig(name, "A log row as a stratigraphic unit", W, H, outdir)
    f.text(50, 40, "Three rows of the WD1 log, three units, each meeting the next", 26, True, anchor="start")
    f.text(50, 76, "Table 1 of the WD1 core, three consecutive rows; the depths are decimals, the description is the label, strat:meets runs downwards.", 19, color=MUTED, anchor="start", maxw=W - 100)
    for i, (title, sub, rows) in enumerate(panels):
        CC.draw_card(f, x0 + i * (pw + gap), top, pw, ph, title, sub, rows, F.OWN_FILL["strat"], dashed=True)
    f.text(50, H - 62, f"Dashed: the strat: classes are planned in geo-lod, and the pipeline does not write WD1 yet; these {len(D.rows)} units are built from the CSV for this page.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 32, "A row that the log leaves undescribed is still a unit with its depths: the log is a chain of intervals, whatever it says about them.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"marker": cur(D.units[D.marker]), "units": len(D.rows)}


def log_fig(D: Wd1Log, stats: dict, outdir: Path, name: str) -> Fig:
    """The whole log as one bar from top to bottom, one segment per unit, and the three counts the query returns."""
    W, H = 1900, 570
    x0, x1, y0, bh = 70, 1830, 150, 90
    top, bottom = stats["top"], stats["bottom"]
    X = lambda d: x0 + (float(d) - top) / (bottom - top) * (x1 - x0)
    f = Fig(name, "The WD1 log as a chain of units", W, H, outdir)
    f.text(50, 40, f"The log is {stats['units']} units, from {top:g} to {bottom:g} m, and strat:meets links each to the next", 26, True, anchor="start")
    f.text(50, 76, "One segment per strat:StratigraphicUnit, by depth; the counts come from the query below, compared with a count made from the CSV.", 19, color=MUTED, anchor="start", maxw=W - 100)
    for a, b, t in D.rows:
        if "tephra" not in t.lower():
            f.rect(X(a), y0, X(b) - X(a), bh, PLAIN if t.startswith("---") else LITHO, "none")
    for a, b, t in D.rows:
        if "tephra" in t.lower():
            f.rect(X(a), y0, max(X(b) - X(a), 2.5), bh, TEPHRA, "none")
    f.rect(x0, y0, x1 - x0, bh, "none", BLACK, 0, 1)
    d = 0
    while d <= bottom:
        f.line(X(d), y0 + bh, X(d), y0 + bh + 9, m=None, w=1.2, color=BLACK)
        f.text(X(d), y0 + bh + 30, f"{d} m", 17, color=MUTED)
        d += 10
    tiles = [(f"{stats['units']}", "strat:StratigraphicUnit", "one per log row"), (f"{stats['tephra']}", "of them strat:TephraLayer", "rows that name a tephra"),
             (f"{stats['links']}", "units that are met by another", "strat:meets, from the unit above"), (f"{stats['gaps']}", "depth gaps in the chain", "where a unit does not touch the next")]
    tw_, tx = 410, 70
    for i, (big, line1, line2) in enumerate(tiles):
        x = tx + i * (tw_ + 40)
        f.rect(x, 330, tw_, 130, "#fbfbf9", "#bdbbb2", 10, 1.2)
        f.text(x + 20, 378, big, 40, True, anchor="start")
        f.text(x + 20, 416, line1, 18, anchor="start", maxw=tw_ - 30)
        f.text(x + 20, 442, line2, 16, color=MUTED, anchor="start", maxw=tw_ - 30)
    f.rect(70, 503, 22, 22, LITHO, BLACK, 3)
    f.text(102, 514, "lithological unit", 17, color=MUTED, anchor="start")
    f.rect(290, 503, 22, 22, TEPHRA, BLACK, 3)
    f.text(322, 514, "tephra layer", 17, color=MUTED, anchor="start")
    f.rect(480, 503, 22, 22, PLAIN, BLACK, 3)
    f.text(512, 514, "not described", 17, color=MUTED, anchor="start")
    f.text(50, H - 22, "Illustrative instances, built from Table 1 of the WD1 core; the strat: classes are planned.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f
