"""Figures of the cluster pages: one graph per cluster, and data figures drawn from the graph and the SISAL tables.

The cluster graph is the readable counterpart of model_figs.relations_fig. It draws only the classes of one cluster, a
subclass arrow where a class specialises another one of the cluster, and one arrow per object property that has a
member of the cluster at one end. A class outside the cluster appears as a dashed edge node that names its own cluster,
so a relation is never dropped, but the figure does not have to carry the rest of the model.

The data figures read `SISAL/rdf/sisal_v3_dating.ttl` and `data/derived/sisal/tables/`. Every number printed on a figure
is counted from there; nothing is typed in.

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import yaml
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

import model_data as md
import model_figs as F
from build import MUTED, Fig, tw

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
GEOLOD = "http://w3id.org/geo-lod/"
STRAT = "http://w3id.org/geo-lod/strat/"
BLACK = "#000000"
GRID = "#d8d6ce"
INK = "#1f1f1d"

# Display names of the SISAL age models; the key is what the graph carries after geolod:AgeModel_.
MODEL_NAME = {"lin_interp": "Linear interpolation", "lin_reg": "Linear regression", "bchron": "Bchron", "bacon": "Bacon",
              "oxcal": "OxCal", "copra": "COPRA", "stalage": "StalAge", "original": "As published"}
MODEL_ORDER = ["lin_interp", "lin_reg", "bchron", "bacon", "oxcal", "copra", "stalage", "original"]
# Okabe-Ito, chosen for being told apart by colour-blind readers; the series are also labelled at the line end.
MODEL_COLOUR = {"lin_interp": "#0072B2", "lin_reg": "#56B4E9", "bchron": "#009E73", "bacon": "#E69F00", "oxcal": "#D55E00",
                "copra": "#CC79A7", "stalage": "#000000", "original": "#7a7a74"}


# ------------------------------------------------------------------ clusters

def load_clusters(M: md.Model) -> list[dict]:
    """clusters.yaml, checked against the ontology: every geolod: class in exactly one cluster, every name a class."""
    clusters = yaml.safe_load((HERE / "clusters.yaml").read_text(encoding="utf-8"))
    by_curie = {c.curie: c for c in M.classes.values()}
    owner: dict[str, str] = {}
    problems = []
    for cl in clusters:
        cl["iris"] = []
        for cur in cl["classes"]:
            if cur not in by_curie:
                problems.append(f"clusters.yaml: {cur} ({cl['id']}) is not a class of the ontology")
                continue
            if cur in owner:
                problems.append(f"clusters.yaml: {cur} is in both {owner[cur]} and {cl['id']}")
            owner[cur] = cl["id"]
            cl["iris"].append(by_curie[cur].iri)
    missing = sorted(c.curie for c in M.classes.values() if c.ns == "geolod" and c.curie not in owner)
    if missing:
        problems.append("clusters.yaml: geolod: classes in no cluster: " + ", ".join(missing))
    if problems:
        raise ValueError("\n".join(problems))
    return clusters


def cluster_of(clusters: list[dict], iri: str) -> dict | None:
    for cl in clusters:
        if iri in cl["iris"]:
            return cl
    return None


# ------------------------------------------------------------------ cluster graph

fit_ = F.fit


def cluster_graph_fig(M: md.Model, clusters: list[dict], cl: dict, outdir: Path, name: str) -> Fig:
    members = set(cl["iris"])

    def lab(iri):
        cur = M.curie(iri)
        return cur.split(":", 1)[1] if cur.startswith("geolod:") else cur

    # relations with a member at one end
    rel = []                                   # (domain, range, property label)
    for p in sorted(M.props.values(), key=lambda p: p.curie):
        if p.kind != "object":
            continue
        for d in p.domains:
            for r in p.ranges:
                if d != r and (d in members or r in members):
                    rel.append((d, r, p.local))
    subs = sorted((c, q) for c in members for q in M.parents(c) if q in members)

    inner_rel = [(d, r, l) for d, r, l in rel if d in members and r in members]
    # layer of an inner node: longest chain of inner relations and subclass arrows that ends at it
    preds = defaultdict(set)
    for d, r, _ in inner_rel:
        preds[r].add(d)
    for c, q in subs:
        preds[c].add(q)                        # the subclass sits to the right of its superclass

    layer: dict[str, int] = {}

    def lay(n, trail=()):
        if n in layer:
            return layer[n]
        if n in trail:
            return 0
        layer[n] = 1 + max((lay(p, trail + (n,)) for p in sorted(preds[n])), default=-1)
        return layer[n]

    for n in sorted(members, key=M.curie):
        lay(n)

    # nodes with no relation at all form a strip below the graph
    touched = {n for d, r, _ in rel for n in (d, r)} | {n for s in subs for n in s}
    loose = sorted((n for n in members if n not in touched), key=M.curie)
    inner = [n for n in sorted(members, key=M.curie) if n in touched]

    # edge nodes: classes outside the cluster, once on the left (they are the domain) and once on the right (the range)
    left_edge = sorted({d for d, r, _ in rel if d not in members}, key=M.curie)
    right_edge = sorted({r for d, r, _ in rel if r not in members}, key=M.curie)
    inner_layers = max((layer[n] for n in inner), default=0) + 1
    cols: list[list[tuple[str, str]]] = [[("edge", n) for n in left_edge]]
    for k in range(inner_layers):
        cols.append([("in", n) for n in inner if layer[n] == k])
    cols.append([("edge", n) for n in right_edge])
    cols_ix = {"L": 0, "R": len(cols) - 1}
    node_col = {}
    for ci, c in enumerate(cols):
        for kind, n in c:
            node_col[(kind, n, "L" if ci == 0 else "R" if ci == len(cols) - 1 and kind == "edge" else "I")] = ci
    used_cols = [i for i, c in enumerate(cols) if c]

    # order inside a column by the mean position of the neighbours already placed; two passes are enough at this size
    pos: dict[tuple[str, str], float] = {}
    for ci in used_cols:
        for i, key in enumerate(cols[ci]):
            pos[key] = i
    nbrs = defaultdict(set)

    def key_of(n, side):
        return ("in", n) if n in members else ("edge", n)

    for d, r, _ in rel:
        kd = ("in", d) if d in members else ("edge", d)
        kr = ("in", r) if r in members else ("edge", r)
        nbrs[kd].add(kr)
        nbrs[kr].add(kd)
    for c, q in subs:
        nbrs[("in", c)].add(("in", q))
        nbrs[("in", q)].add(("in", c))
    for _ in range(4):
        for ci in used_cols:
            cols[ci].sort(key=lambda k: (sum(pos[m] for m in nbrs[k]) / max(len(nbrs[k]), 1), M.curie(k[1])))
            for i, key in enumerate(cols[ci]):
                pos[key] = i

    # geometry
    if set(left_edge) & set(right_edge):
        raise ValueError(f"{name}: a class outside the cluster is both a domain and a range of it; the figure would need it twice")
    size, bh = 19, 62
    keycol = {key: ci for ci in used_cols for key in cols[ci]}
    rank = {ci: i for i, ci in enumerate(used_cols)}

    def node_key(n):
        return ("in", n) if n in members else ("edge", n)

    def anchor_of(n):
        a, _ = M.anchors(n)
        return ("→ " + M.curie(a[0]) + (f" +{len(a) - 1}" if len(a) > 1 else "")) if a else ""

    arrows = [("rel", d, r, l) for d, r, l in rel] + [("sub", c, q, "") for c, q in subs]
    # arrows are drawn from the first to the second class; a subclass arrow runs from the subclass to its superclass
    span = {i: abs(rank[keycol[node_key(a)]] - rank[keycol[node_key(b)]]) for i, (_, a, b, _) in enumerate(arrows)}
    channel = [i for i in range(len(arrows)) if span[i] > 1]
    colw = {}
    for ci in used_cols:
        colw[ci] = min(340, max(max(tw(lab(n), size, True) + 34, (tw(anchor_of(n), 14) + 26) if k == "in" else 0) for k, n in cols[ci]))
        if any(k == "edge" for k, _ in cols[ci]):
            colw[ci] = max(colw[ci], 210)
    ncols = len(used_cols)
    near = [tw(l, 17) + 12 for i, (_, _, _, l) in enumerate(arrows) if l and span[i] <= 1]
    gap = max(120.0, max(near, default=0) + 40)
    W = max(1750, int(100 + sum(colw.values()) + gap * max(ncols - 1, 0)))
    xs, x = {}, 50.0 + (W - 100 - sum(colw.values()) - gap * max(ncols - 1, 0)) / 2
    for ci in used_cols:
        xs[ci] = x
        x += colw[ci] + gap
    pitch = 96
    top = 70 + 34 * len(channel)
    rows = max(len(cols[ci]) for ci in used_cols)
    graph_h = rows * pitch
    loose_h = 0
    per_row = max(1, int((W - 100) // 250))
    if loose:
        loose_h = 80 + math.ceil(len(loose) / per_row) * 64
    H = int(top + graph_h + loose_h + 130)
    f = Fig(name, f"Cluster: {cl['title']}", W, H, outdir)

    box = {}
    for ci in used_cols:
        n = len(cols[ci])
        y0 = top + (graph_h - n * pitch) / 2
        for i, key in enumerate(cols[ci]):
            box[key] = (xs[ci], y0 + i * pitch + (pitch - bh) / 2, colw[ci], bh)

    def endpoint(n):
        return box[node_key(n)]

    # ports: spread the arrow ends along the side of a box so that parallel arrows do not share a point
    out_ports, in_ports = defaultdict(list), defaultdict(list)
    for ai, (kind, a, b, l) in enumerate(arrows):
        out_ports[a].append(ai)
        in_ports[b].append(ai)

    def y_of(node, lst, ai, other):
        x0, y0, w0, h0 = endpoint(node)
        order = sorted(lst, key=lambda j: (endpoint(other(j))[1], j))
        return y0 + h0 * (order.index(ai) + 1) / (len(order) + 1)

    labels, late = [], []
    for ai, (kind, a, b, l) in enumerate(arrows):
        sx, sy, sw, sh = endpoint(a)
        dx, dy, dw, dh = endpoint(b)
        y1 = y_of(a, out_ports[a], ai, lambda j: arrows[j][2])
        y2 = y_of(b, in_ports[b], ai, lambda j: arrows[j][1])
        mk = "t" if kind == "sub" else "a"
        if sx + sw <= dx:
            x1, x2 = sx + sw, dx - 3
        else:
            x1, x2 = sx, dx + dw + 3
        if ai in channel:
            k = channel.index(ai)
            ty = top - 34 * (k + 1) + 10
            f.path(f"M {x1:.1f} {y1:.1f} C {x1 + 70:.1f} {ty:.1f} {x2 - 70:.1f} {ty:.1f} {x2:.1f} {y2:.1f}", mk)
            late.append(((x1 + x2) / 2, (y1 + y2) / 8 + 0.75 * ty, l))
        else:
            f.line(round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1), mk)
            if l:
                labels.append(((x1 + x2) / 2, (y1 + y2) / 2, l))
    # labels on top of the arrows, with a white backing so that the line does not run through the letters
    for lx, ly, l in labels:
        w = tw(l, 17) + 12
        f.rect(round(lx - w / 2, 1), round(ly - 12, 1), round(w, 1), 24, "#ffffff", "none", 4)
        f.text(round(lx, 1), round(ly, 1), l, 17, color=MUTED)

    for (kind, n), (x0, y0, w0, h0) in sorted(box.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        fill = F.fill_of(n)
        if kind == "in":
            f.raw(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w0:.1f}" height="{h0:.1f}" rx="8" fill="{fill}" stroke="{BLACK}" stroke-width="1.2"/>')
            a = anchor_of(n)
            f.text(x0 + w0 / 2, y0 + h0 / 2 - (9 if a else 0), fit_(lab(n), size, w0 - 14), size, True, BLACK, maxw=w0 - 10)
            if a:
                f.text(x0 + w0 / 2, y0 + h0 / 2 + 14, a, 14, color="#3a3935", maxw=w0 - 8)
        else:
            other = cluster_of(clusters, n)
            F.nbox(f, x0, y0, w0, h0 - 8 if other else h0, lab(n), fill, dash=True, size=size)
            if other:
                f.text(x0 + w0 / 2, y0 + h0 - 2, "→ " + other["short"], 15, color=MUTED, maxw=w0 - 8)

    # labels of the long arrows come last, so that no box covers them
    for lx, ly, l in late:
        w = tw(l, 17) + 12
        f.rect(round(lx - w / 2, 1), round(ly - 12, 1), round(w, 1), 24, "#ffffff", "none", 4)
        f.text(round(lx, 1), round(ly, 1), l, 17, color=MUTED)

    if loose:
        y = top + graph_h + 36
        f.text(50, y, "Classes of the cluster with no relation of their own in the ontology", 18, color=MUTED, anchor="start")
        wl = max(230, math.ceil(max(tw(lab(n), size, True) for n in loose) + 34))      # a long name must not be cut
        pr = per_row if wl == 230 else max(1, (W - 100) // (wl + 20))
        for i, n in enumerate(loose):
            F.nbox(f, 50 + (i % pr) * (wl + 20), y + 22 + (i // pr) * 64, wl, bh, lab(n), F.fill_of(n), size=size)

    own = [("geolod", "geolod:")]
    if any(md.ns_key(n) == "strat" for n in members | set(left_edge) | set(right_edge)):
        own.append(("strat", "strat:"))
    iris = [n for n in set(left_edge) | set(right_edge)]
    F.legend(f, H - 70, F.family_items(iris, with_own=own) + [("#ffffff", "dashed: class of another cluster")], note=None)
    f.text(50, H - 26, "Arrows run from domain to range; a hollow head marks a subclass; the second line names the CRM-family class a class reaches. Datatype properties are in the tables.",
           18, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f


# ------------------------------------------------------------------ data

class Dating:
    """The dating graph of SISAL and the SISAL tables, read once."""

    def __init__(self, repo: Path = REPO):
        self.repo = repo
        g = Graph().parse(repo / "SISAL/rdf/sisal_v3_dating.ttl", format="turtle")
        self.g = g
        G = lambda s: URIRef(GEOLOD + s)
        self.points = []            # (entity id, depth mm, age ka, set of model keys)
        for s in g.subjects(RDF.type, URIRef(STRAT + "AgeControlPoint")):
            ent = next(g.objects(s, G("constrainsSpeleothem")), None)
            depth = next(g.objects(s, G("atDepth_mm")), None)
            age = next(g.objects(s, G("ageKaBP")), None)
            models = {str(m).rsplit("AgeModel_", 1)[1] for m in g.objects(s, G("usedInAgeModel"))}
            self.points.append((self._eid(ent), _num(depth), _num(age), models))
        self.hiatuses = []          # (entity id, depth mm, set of model keys)
        for s in g.subjects(RDF.type, G("GrowthHiatus")):
            ent = next(g.objects(s, G("inSpeleothem")), None)
            depth = next(g.objects(s, G("atDepth_mm")), None)
            models = {str(m).rsplit("AgeModel_", 1)[1] for m in g.objects(s, G("respectedByAgeModel"))}
            self.hiatuses.append((self._eid(ent), _num(depth), models))
        if not self.points or not self.hiatuses:
            raise ValueError("sisal_v3_dating.ttl holds no age control points or no hiatuses; the figures have nothing to draw")
        t = repo / "data/derived/sisal/tables"
        self.entity_name = {r["entity_id"]: r["entity_name"] for r in _rows(t / "entity.csv")}
        self.tables = t

    @staticmethod
    def _eid(node) -> str:
        return str(int(str(node).rsplit("entity_", 1)[1]))

    def models(self) -> list[str]:
        seen = {m for _, _, _, ms in self.points for m in ms} | {m for _, _, ms in self.hiatuses for m in ms}
        return [m for m in MODEL_ORDER if m in seen] + sorted(seen - set(MODEL_ORDER))


def _num(lit) -> float | None:
    return float(lit) if isinstance(lit, Literal) else None


def _rows(path: Path):
    with open(path, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def _ticks(lo: float, hi: float, n: int = 6) -> list[float]:
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=raw)
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + 1e-9:
        out.append(round(t, 10))
        t += step
    return out


def _fmt(v: float) -> str:
    return f"{v:g}"


# ------------------------------------------------------------------ hiatus x model

def hiatus_matrix_fig(D: Dating, outdir: Path, name: str) -> tuple[Fig, dict]:
    models = D.models()
    rows = sorted(D.hiatuses, key=lambda h: (D.entity_name.get(h[0], h[0]), h[1] if h[1] is not None else 0))
    cell, rowh = 170, 27
    left, top = 330, 150
    W = left + cell * len(models) + 70
    H = top + rowh * len(rows) + 150
    f = Fig(name, "Which age models treated a hiatus as a break", max(W, 1100), H, outdir)
    W = f.w
    f.text(50, 40, "Which age model treated a growth hiatus as a break", 26, True, anchor="start")
    f.text(50, 76, "One row per hiatus in the graph, one column per age model; a filled cell is geolod:respectedByAgeModel.", 19,
           color=MUTED, anchor="start")
    for j, m in enumerate(models):
        f.text(left + cell * j + cell / 2, top - 26, MODEL_NAME.get(m, m), 17, True, anchor="middle", maxw=cell - 6)
    last = None
    for i, (eid, depth, ms) in enumerate(rows):
        y = top + i * rowh
        if i % 2 == 0:
            f.rect(50, y, W - 100, rowh, "#f6f6f3")
        name_e = D.entity_name.get(eid, f"entity {eid}")
        f.text(60, y + rowh / 2, name_e if name_e != last else "", 17, True, anchor="start", maxw=150)
        last = name_e
        f.text(left - 14, y + rowh / 2, f"{_fmt(depth)} mm" if depth is not None else "", 17, color=MUTED, anchor="end")
        for j, m in enumerate(models):
            cx = left + cell * j + cell / 2
            if m in ms:
                f.raw(f'<circle cx="{cx}" cy="{y + rowh / 2}" r="8" fill="{MODEL_COLOUR.get(m, INK)}" stroke="{BLACK}" stroke-width="1"/>')
            else:
                f.raw(f'<circle cx="{cx}" cy="{y + rowh / 2}" r="3" fill="#c9c7be"/>')
    y = top + len(rows) * rowh + 6
    f.line(50, y, W - 50, y, None, w=1.2, color=INK)
    counts = {m: sum(1 for _, _, ms in rows if m in ms) for m in models}
    f.text(60, y + 28, f"Hiatuses respected, of {len(rows)}", 18, True, anchor="start")
    for j, m in enumerate(models):
        f.text(left + cell * j + cell / 2, y + 28, str(counts[m]), 22, True, color=MODEL_COLOUR.get(m, INK) if m != "stalage" else INK)
    f.text(50, H - 30, "A small dot: the model ran across the hiatus. A hiatus that no model respects carries no geolod:respectedByAgeModel statement.",
           17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"hiatuses": len(rows), "counts": counts, "entities": len({h[0] for h in rows})}


# ------------------------------------------------------------------ control points per model

def control_points_fig(D: Dating, outdir: Path, name: str) -> tuple[Fig, dict]:
    models = D.models()
    total = len(D.points)
    counts = {m: sum(1 for *_, ms in D.points if m in ms) for m in models}
    order = sorted(models, key=lambda m: -counts[m])
    left, barw, top, rowh = 300, 1000, 150, 64
    W, H = 1750, top + rowh * len(order) + 140
    f = Fig(name, "Dating points each age model took as a constraint", W, H, outdir)
    f.text(50, 40, "How many dating points each age model used", 26, True, anchor="start")
    f.text(50, 76, f"{total} strat:AgeControlPoint in the graph; the bar is geolod:usedInAgeModel counted per model.", 19, color=MUTED, anchor="start")
    for t in range(0, 101, 25):
        x = left + barw * t / 100
        f.line(x, top - 14, x, top + rowh * len(order) - 8, None, w=1, color=GRID)
        f.text(x, top - 30, f"{t} %", 16, color=MUTED)
    for i, m in enumerate(order):
        y = top + i * rowh
        share = counts[m] / total
        f.text(left - 18, y + rowh / 2 - 8, MODEL_NAME.get(m, m), 21, True, anchor="end")
        f.rect(left, y + 8, barw, rowh - 32, "#eeede8")
        f.rect(left, y + 8, round(barw * share, 1), rowh - 32, MODEL_COLOUR.get(m, INK), BLACK, 0, 1)
        f.text(left + barw + 18, y + rowh / 2 - 8, f"{counts[m]}  ·  {100 * share:.0f} %", 21, anchor="start")
    f.text(50, H - 30, "A model need not use every point; the share differs from model to model.",
           17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"total": total, "counts": counts}


# ------------------------------------------------------------------ one speleothem, many ages

def pick_speleothem(D: Dating, entity: str = "55") -> str:
    """JAR7 (Jaragua): six models and the published chronology reach it, and it carries a hiatus."""
    return entity


def one_speleothem_fig(D: Dating, outdir: Path, name: str, entity: str = "55") -> tuple[Fig, dict]:
    t = D.tables
    depth = {r["sample_id"]: float(r["depth_sample"]) for r in _rows(t / "sample.csv") if r["entity_id"] == entity}
    series: dict[str, list[tuple[float, float]]] = defaultdict(list)
    keys = [m for m in MODEL_ORDER if m != "original"]
    for r in _rows(t / "sisal_chronology.csv"):
        d = depth.get(r["sample_id"])
        if d is None:
            continue
        for m in keys:
            v = r.get(f"{m}_age")
            if v:
                series[m].append((d, float(v) / 1000))
    for r in _rows(t / "original_chronology.csv"):
        d = depth.get(r["sample_id"])
        if d is not None and r["interp_age"]:
            series["original"].append((d, float(r["interp_age"]) / 1000))
    present = [m for m in MODEL_ORDER if series.get(m)]
    if "stalage" not in present:
        raise ValueError(f"{name}: no StalAge series for entity {entity}; the deviation panel has no reference")
    for m in present:
        series[m].sort()
    ref = dict(series["stalage"])
    hi = [h for h in D.hiatuses if h[0] == entity]
    pts = [p for p in D.points if p[0] == entity and p[1] is not None and p[2] is not None]
    ename = D.entity_name.get(entity, f"entity {entity}")

    xs = [d for m in present for d, _ in series[m]]
    x0, x1 = 0.0, max(xs)
    ys = [a for m in present for _, a in series[m]]
    y0, y1 = min(ys), max(ys)
    dev = {m: [(d, (a - ref[d]) * 1000) for d, a in series[m] if d in ref] for m in present if m != "stalage"}
    dvals = [v for m in dev for _, v in dev[m]]
    dlim = max(abs(min(dvals, default=0)), abs(max(dvals, default=0)), 1)

    W, H = 1750, 1060
    L, R = 130, 80
    pw = W - L - R
    p1t, p1b = 140, 560
    p2t, p2b = 650, 880
    f = Fig(name, f"{ename}: the ages of one speleothem under each age model", W, H, outdir)
    f.text(50, 40, f"One speleothem, {len(present)} age series: {ename}", 26, True, anchor="start")
    f.text(50, 76, "Each line is the age one model gives to every sample of the speleothem (geolod:AgeAssignment, one per model and sample).",
           19, color=MUTED, anchor="start")

    def X(d):
        return L + pw * (d - x0) / (x1 - x0)

    def Y1(a):
        return p1b - (p1b - p1t) * (a - y0) / (y1 - y0)

    for a in _ticks(y0, y1):
        f.line(L, round(Y1(a), 1), L + pw, round(Y1(a), 1), None, w=1, color=GRID)
        f.text(L - 12, round(Y1(a), 1), _fmt(a), 17, color=MUTED, anchor="end")
    f.raw(f'<text transform="translate(38 {(p1t + p1b) / 2}) rotate(-90)" text-anchor="middle" dominant-baseline="central" font-family="Fira Sans" font-size="18" fill="{MUTED}">age (ka BP)</text>')
    for d in _ticks(x0, x1, 8):
        f.line(round(X(d), 1), p1t, round(X(d), 1), p1b, None, w=1, color=GRID)
        f.text(round(X(d), 1), p2b + 22, _fmt(d), 17, color=MUTED)
    f.rect(L, p1t, pw, p1b - p1t, "none", INK, 0, 1)

    def poly(seq, Y, colour, wd):
        pts_ = " ".join(f"{X(d):.1f},{Y(a):.1f}" for d, a in seq)
        f.raw(f'<polyline points="{pts_}" fill="none" stroke="{colour}" stroke-width="{wd}" stroke-linejoin="round"/>')

    for m in present:
        poly(series[m], Y1, MODEL_COLOUR.get(m, INK), 3.2 if m == "stalage" else 2.0)
    for _, d, _ in hi:
        if d is not None:
            for top_, bot in ((p1t, p1b), (p2t, p2b)):
                f.line(round(X(d), 1), top_, round(X(d), 1), bot, None, dash=True, w=1.8, color="#9a3412")
    f.text(L, p1t - 14, "dashed: geolod:GrowthHiatus" if hi else "", 17, color="#9a3412", anchor="start")
    for _, d, a, _ in pts:
        f.raw(f'<circle cx="{X(d):.1f}" cy="{Y1(a):.1f}" r="6" fill="#ffffff" stroke="{BLACK}" stroke-width="2"/>')
    unused = sum(1 for p in pts if not p[3])
    note_pts = "circles: dating points (strat:AgeControlPoint)" + (f"; {unused} of {len(pts)} used by no model" if unused else "")
    f.text(L + pw, p1t - 14, note_pts, 17, color=MUTED, anchor="end")

    # deviation panel
    def Y2(v):
        return (p2t + p2b) / 2 - (p2b - p2t) / 2 * v / dlim * 0.92

    f.text(L, p2t - 22, "Difference from StalAge, in years", 19, True, anchor="start")
    for v in _ticks(-dlim, dlim, 4):
        f.line(L, round(Y2(v), 1), L + pw, round(Y2(v), 1), None, w=2 if v == 0 else 1, color=INK if v == 0 else GRID)
        f.text(L - 12, round(Y2(v), 1), _fmt(v), 17, color=MUTED, anchor="end")
    f.rect(L, p2t, pw, p2b - p2t, "none", INK, 0, 1)
    for m in dev:
        poly(dev[m], Y2, MODEL_COLOUR.get(m, INK), 2.0)
    f.text(L + pw / 2, p2b + 52, "depth from the top of the speleothem (mm)", 18, color=MUTED)

    # legend, one entry per series with the number of samples it reaches
    n_all = len(depth)
    lx, ly = 50, H - 80
    for m in present:
        label = f"{MODEL_NAME.get(m, m)} · {len(series[m])} of {n_all}"
        w = 40 + tw(label, 17) + 28
        if lx + w > W - 40:
            lx, ly = 50, ly + 28
        f.line(lx, ly, lx + 30, ly, None, w=4, color=MODEL_COLOUR.get(m, INK))
        f.text(lx + 40, ly, label, 17, anchor="start")
        lx += w
    by_depth = defaultdict(list)
    for _, d, a, _ in pts:
        by_depth[d].append(a)
    clash = sorted(d for d, a in by_depth.items() if len(a) > 1 and max(a) - min(a) > 0.5)
    tail = "Not every model reaches every sample; the second figure number is the count of samples of the speleothem."
    if clash:
        tail += f" {len(clash)} depth carries two dating points more than 0.5 ka apart ({', '.join(_fmt(d) + ' mm' for d in clash)})."
    f.text(50, H - 26, tail, 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    spread = {m: max(abs(v) for _, v in dev[m]) for m in dev if dev[m]}
    return f, {"entity": ename, "series": len(present), "samples": n_all, "hiatus": len(hi), "points": len(pts), "spread": spread}


# ------------------------------------------------------------------ the modelling pattern

def age_pattern_fig(M: md.Model, D: Dating, outdir: Path, name: str, entity: str = "55") -> tuple[Fig, dict]:
    """One sample, drawn twice: its age as a plain property, and as the assignments sisal_rdf.add_ages writes.

    The pattern is read from the ontology (classes, properties, the CRM anchor) and the values from the SISAL tables the
    graph is written from. The assignment nodes are not in the committed Turtle, they belong to the large graph the
    pipeline writes; the figure says so."""
    for need in ("geolod:AgeAssignment", "geolod:AgeModel", "geolod:SpeleothemSample"):
        if need not in {c.curie for c in M.classes.values()}:
            raise ValueError(f"{name}: {need} is not a class of the ontology")
    for need in ("geolod:ageModel", "geolod:ageKaBP", "geolod:assignmentStatus"):
        if need not in {p.curie for p in M.props.values()}:
            raise ValueError(f"{name}: {need} is not a property of the ontology")
    ac = next(c for c in M.classes.values() if c.curie == "geolod:AgeAssignment")
    anchors, _ = M.anchors(ac.iri)
    t = D.tables
    depth = {r["sample_id"]: float(r["depth_sample"]) for r in _rows(t / "sample.csv") if r["entity_id"] == entity}
    ages: dict[str, dict[str, float]] = defaultdict(dict)
    for r in _rows(t / "sisal_chronology.csv"):
        if r["sample_id"] in depth:
            for m in ("lin_interp", "bchron", "stalage"):
                if r.get(f"{m}_age"):
                    ages[r["sample_id"]][m] = float(r[f"{m}_age"]) / 1000
    full = sorted((sid for sid, a in ages.items() if len(a) == 3), key=lambda sid: depth[sid])
    if not full:
        raise ValueError(f"{name}: no sample of entity {entity} with three ages")
    sid = full[len(full) // 2]
    keys = ["lin_interp", "bchron", "stalage"]
    leading = "lin_interp" if "lin_interp" in ages[sid] else None      # the rule of SISAL/sisal_rdf.py add_ages
    sample_iri = f"sisal:sample_{int(sid):07d}"

    W, H = 1750, 1130
    f = Fig(name, "One age as a property, one age as an assignment", W, H, outdir)
    f.text(50, 40, "Why an age is an assignment and not a property", 26, True, anchor="start")
    f.text(50, 76, f"One sample of {D.entity_name.get(entity, entity)} ({sample_iri}, depth {_fmt(depth[sid])} mm), drawn two ways.", 19, color=MUTED, anchor="start")

    def node(x, y, w, h, title, sub=None, fill="#ffffff", dash=False, tsz=19):
        ds = ' stroke-dasharray="7 5" stroke-width="1.8"' if dash else ' stroke-width="1.2"'
        f.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{BLACK}"{ds}/>')
        if sub:
            f.text(x + w / 2, y + h / 2 - 10, title, tsz, True, BLACK, maxw=w - 12)
            f.text(x + w / 2, y + h / 2 + 14, sub, 14, color="#3a3935", maxw=w - 10)
        else:
            f.text(x + w / 2, y + h / 2, title, tsz, True, BLACK, maxw=w - 12)

    def arrow(x1, y1, x2, y2, label):
        f.line(round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1), "a")
        w = tw(label, 17) + 12
        f.rect(round((x1 + x2) / 2 - w / 2, 1), round((y1 + y2) / 2 - 12, 1), round(w, 1), 24, "#ffffff", "none", 4)
        f.text(round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1), label, 17, color=MUTED)

    gl, st, own = F.OWN_FILL["geolod"], F.FAM_FILL["crm"], "#f6f6f3"
    # top: the property
    f.text(50, 130, "As a property of the sample", 22, True, anchor="start")
    node(50, 160, 360, 62, sample_iri, "a geolod:SpeleothemSample", gl)
    arrow(410, 191, 760, 191, "geolod:ageKaBP")
    node(760, 165, 230, 52, f"{ages[sid]['lin_interp']:.6f}", "xsd:decimal", own)
    f.text(1030, 180, "One number. Which model made it, whether another model gives a different one,", 18, color="#9a3412", anchor="start")
    f.text(1030, 206, "and whether it is the age to follow: the graph does not say.", 18, color="#9a3412", anchor="start")
    f.line(50, 275, W - 50, 275, None, w=1.2, color=GRID)

    # bottom: the assignments
    f.text(50, 320, "As geolod:AgeAssignment, one per model and sample", 22, True, anchor="start")
    pitch, y0 = 235, 360
    mid = y0 + pitch * 1.5 - 30
    node(50, mid - 31, 300, 62, sample_iri, "a geolod:SpeleothemSample", gl)
    for i, key in enumerate(keys):
        y = y0 + i * pitch
        iri = f"sisal:age_{int(sid):07d}_{key}"
        node(620, y + 52, 430, 74, iri, f"a geolod:AgeAssignment  → {M.curie(anchors[0])}" if anchors else "a geolod:AgeAssignment", gl)
        arrow(620, y + 89, 350, mid - 12 + 12 * i, "crm:P140_assigned_attribute_to")
        for j, (prop, tgt, sub, fill) in enumerate([
                ("geolod:ageModel", f"geolod:AgeModel_{key}", "a geolod:AgeModel", gl),
                ("geolod:ageKaBP", f"{ages[sid][key]:.6f}", "xsd:decimal", own),
                ("geolod:assignmentStatus", "geolod:LeadingAssignment" if key == leading else "geolod:AlternativeAssignment", "a geolod:AssignmentStatus", gl)]):
            ty = y + j * 66
            node(1330, ty, 370, 54, tgt, sub, fill)
            arrow(1050, y + 89, 1330, ty + 27, prop)
    f.text(50, H - 70, f"The ontology anchors geolod:AgeAssignment in {M.curie(anchors[0]) if anchors else 'the CRM family'}; the values are read from the SISAL tables the graph is written from.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.text(50, H - 40, "IRIs follow sisal_rdf.add_ages. The assignment nodes belong to the large graph written by the pipeline; the committed Turtle holds the dating points and hiatuses only.", 17, color=MUTED, anchor="start", maxw=W - 100)
    f.save()
    return f, {"sample": sample_iri, "models": keys}
