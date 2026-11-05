"""Cards of triples for the pattern figures of the cluster pages.

A card is a panel with a title and rows. A row is a property and its object: a node (drawn as a box with its class under
the name) or a literal (drawn as text on the right). The caller reads every row from the graph; nothing is typed in here.

Layout is deterministic and text widths come from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF

import model_figs as F
from build import MUTED, Fig

BLACK, INK = "#000000", "#1f1f1d"
ROW_LIT, ROW_NODE, HEAD = 42, 86, 96

Row = tuple[str, str, str, str]            # (property, "node" | "lit", name or value, class line)


def node_class(g: Graph, node: URIRef, nm) -> str:
    """The class a node is typed with, for display: a geolod class if there is one, else any other, never owl:NamedIndividual."""
    types = sorted((t for t in g.objects(node, RDF.type) if t != OWL.NamedIndividual), key=str)
    types.sort(key=lambda t: not str(t).startswith("http://w3id.org/geo-lod/"))
    return types[0].n3(nm) if types else ""


def short_iri(iri) -> str:
    """An IRI with no prefix, shortened for a box: host, an ellipsis and the last path segment."""
    parts = str(iri).split("://", 1)[-1].rstrip("/").split("/")
    return parts[0] if len(parts) == 1 else f"{parts[0]}/…/{parts[-1]}"


def number(v) -> str:
    return format(float(v), "g")


def card_row(g: Graph, subject: URIRef, pred: URIRef, kind: str, suffix: str = "", extra=None) -> Row:
    """One row, read from the graph. A missing statement stops the build: a figure must not draw what is not there."""
    nm = g.namespace_manager
    v = min(g.objects(subject, pred), key=str, default=None)      # several values: the first in sorted order, so the figure is deterministic
    if v is None:
        raise ValueError(f"{subject} has no {pred}")
    if kind == "node":
        if not isinstance(v, URIRef):
            raise ValueError(f"{subject} {pred}: expected a node, found {v!r}")
        cls = node_class(g, v, nm) + (extra(v) if extra else "")
        return (pred.n3(nm), "node", v.n3(nm), cls)
    if isinstance(v, Literal):
        numeric = v.datatype is not None and str(v.datatype).rsplit("#", 1)[-1] in ("decimal", "integer", "double", "float")
        txt = number(v) if numeric else str(v)
        return (pred.n3(nm), "lit", txt + suffix, "")
    return (pred.n3(nm), "lit", v.n3(nm), "")


def card_height(rows: list[Row]) -> int:
    return HEAD + sum(ROW_NODE if r[1] == "node" else ROW_LIT for r in rows) + 18


def draw_card(f: Fig, x: float, y: float, w: float, h: float, title: str, sub: str, rows: list[Row], fill: str) -> None:
    f.rect(x, y, w, h, "#fbfbf9", "#bdbbb2", 10, 1.2)
    f.text(x + 18, y + 30, title, 21, True, anchor="start", maxw=w - 30)
    f.text(x + 18, y + 62, sub, 16, color=MUTED, anchor="start", maxw=w - 30)
    yy = y + HEAD
    for pred, kind, val, cls in rows:
        if kind == "node":
            f.text(x + 18, yy + 14, pred, 16, color=MUTED, anchor="start", maxw=w - 40)
            bx, bw = x + 18, w - 36
            f.raw(f'<rect x="{bx}" y="{yy + 30}" width="{bw}" height="{ROW_NODE - 38}" rx="7" fill="{fill}" stroke="{BLACK}" stroke-width="1.1"/>')
            f.text(bx + bw / 2, yy + 30 + 14, F.fit(val, 17, bw - 16, True), 17, True, BLACK, maxw=bw - 8)
            f.text(bx + bw / 2, yy + 30 + 33, F.fit(cls, 14, bw - 16), 14, color="#3a3935", maxw=bw - 8)
            yy += ROW_NODE
        else:
            f.text(x + 18, yy + ROW_LIT / 2, pred, 16, color=MUTED, anchor="start", maxw=w * .5)
            f.text(x + w - 18, yy + ROW_LIT / 2, F.fit(val, 18, w * .5 - 30), 18, color=INK, anchor="end")
            yy += ROW_LIT
