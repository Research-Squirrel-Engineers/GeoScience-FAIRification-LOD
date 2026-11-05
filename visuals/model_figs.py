"""Data-model figures in the house style of the slide figures, drawn from the ontology files and from the graph.

Nothing here knows a class or property by name. The hierarchy, relation and coverage figures read model_data.Model; the
instance figures read the published RDF. A figure therefore cannot show a class the ontology does not declare, and a
change in the ontology changes the figure instead of making it wrong.

    hierarchy_fig   rdfs:subClassOf as a left-to-right tree, CRM-family classes at the roots
    relations_fig   object properties as arrows from domain to range
    coverage_fig    one card per CRM-family anchor, with the geo-lod classes that reach it
    crosswalk_fig   every class on the left, the classes it passes on the way, its CRM-family anchor on the right
    instance_fig    one resource of the graph with its neighbours, as it stands in the RDF

Layout is deterministic: sorted iteration, no random numbers, text widths from the bundled Fira Sans (build.tw).
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

import build as B
import model_data as md
from build import AN, CLS, GL, INST, MUTED, REAL, ST, TERM, Fig, tw

OWN_FILL = {"geolod": GL[0], "strat": ST[0], "an": AN[0]}
FAM_FILL = {"crm": "#d4e1f5", "sci": "#ffcc99", "arch": "#e3d5f0", "geo": "#dbe9d3", None: "#e4e4e0"}
FAM_ORDER = {"crm": 0, "sci": 1, "arch": 2, "geo": 3, None: 4}
BLACK = "#000000"


def fill_of(iri: str) -> str:
    ns = md.ns_key(iri)
    return OWN_FILL[ns] if ns else FAM_FILL.get(md.family(iri), FAM_FILL[None])


def fit(text: str, size: int, maxw: float, med: bool = False) -> str:
    """Shorten with an ellipsis until the text fits; the figures must not raise over a long label from the data."""
    if tw(text, size, med) <= maxw:
        return text
    while text and tw(text + "…", size, med) > maxw:
        text = text[:-1]
    return text + "…"


def nbox(f: Fig, x, y, w, h, text, fill, dash=False, size=19, color=BLACK):
    ds = ' stroke-dasharray="7 5" stroke-width="1.8"' if dash else ' stroke-width="1.2"'
    f.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="{fill}" stroke="{BLACK}"{ds}/>')
    f.text(x + w / 2, y + h / 2, fit(text, size, w - 14, True), size, True, color, maxw=w - 10)


def legend(f: Fig, y, items, note=None):
    f.legend(y, [((fill, BLACK, BLACK), text) for fill, text in items])
    if note:
        f.text(50, f.h - 26, note, 18, color=MUTED, anchor="start", maxw=f.w - 100)


def family_items(iris, with_own=()):
    items = [(OWN_FILL[k], t) for k, t in with_own]
    seen = {}
    for i in iris:
        if not md.ns_key(i):
            seen[md.family(i)] = True
    names = {"crm": "CIDOC CRM", "sci": "CRMsci", "arch": "CRMarchaeo", "geo": "CRMgeo", None: "other vocabulary"}
    items += [(FAM_FILL[k], names[k]) for k in sorted(seen, key=lambda k: FAM_ORDER[k])]
    return items


# ------------------------------------------------------------------ hierarchy

def hierarchy_fig(M: md.Model, outdir: Path, name: str, title: str, mods: tuple[str, ...], note: str) -> Fig:
    own = M.classes_of(*mods)
    ownset = {c.iri for c in own}
    label_of = {c.iri: c.local for c in own}

    def lab(iri):
        return label_of.get(iri) or M.curie(iri)

    def primary(iri):
        ps = M.parents(iri)
        if not ps or (md.family(iri) and iri not in ownset):
            return None
        inside = [p for p in ps if p in ownset]
        fam = [p for p in ps if md.family(p)]
        return (inside or fam or ps)[0]

    parent: dict[str, str | None] = {}

    def chain(iri):
        while iri not in parent:
            p = primary(iri)
            parent[iri] = p
            if p is None:
                break
            iri = p

    for c in own:
        chain(c.iri)
    extras = []
    for c in own:
        for q in M.parents(c.iri):
            if q != parent[c.iri]:
                extras.append((c.iri, q))
                chain(q)

    children = defaultdict(list)
    for n, p in parent.items():
        if p:
            children[p].append(n)
    for p in children:
        children[p].sort(key=M.curie)
    roots = sorted((n for n, p in parent.items() if p is None), key=lambda n: (FAM_ORDER[md.family(n)], M.curie(n)))

    depth = {}

    def dep(n):
        if n not in depth:
            depth[n] = 0 if parent[n] is None else dep(parent[n]) + 1
        return depth[n]

    for n in parent:
        dep(n)
    ncol = max(depth.values()) + 1
    colw = [min(410, max(tw(lab(n), 19, True) + 30 for n in parent if depth[n] == d)) for d in range(ncol)]
    gap = 96
    if math.fsum(colw) + gap * (ncol - 1) > 1750 - 100:
        raise ValueError(f"{name}: {ncol} columns do not fit")
    xs = [50 + math.fsum(colw[:d]) + gap * d for d in range(ncol)]

    ypos, cur = {}, [0]

    def place(n):
        ch = children.get(n, [])
        if not ch:
            ypos[n] = cur[0]
            cur[0] += 1
            return
        for c in ch:
            place(c)
        ypos[n] = (ypos[ch[0]] + ypos[ch[-1]]) / 2

    for r in roots:
        place(r)
    rowh, top, bh = 44, 40, 32
    f = Fig(name, title, 1750, int(top + cur[0] * rowh + 120), outdir)
    cy = {n: top + ypos[n] * rowh + bh / 2 for n in parent}
    for n, p in parent.items():
        if p:
            mx = xs[depth[n]] - gap / 2
            f.path(f"M {xs[depth[n]]:.1f} {cy[n]:.1f} L {mx:.1f} {cy[n]:.1f} L {mx:.1f} {cy[p]:.1f} L {xs[depth[p]] + colw[depth[p]] + 2:.1f} {cy[p]:.1f}", "t")
    for n, q in extras:
        mx = xs[depth[n]] - gap / 2 + 16
        f.path(f"M {xs[depth[n]]:.1f} {cy[n] + 6:.1f} L {mx:.1f} {cy[n] + 6:.1f} L {mx:.1f} {cy[q]:.1f} L {xs[depth[q]] + colw[depth[q]] + 2:.1f} {cy[q]:.1f}", "t", True)
    for n in parent:
        nbox(f, xs[depth[n]], cy[n] - bh / 2, colw[depth[n]], bh, lab(n), fill_of(n),
             dash=bool(md.ns_key(n)) and n not in ownset)
    items = family_items(parent, [(k, t) for k, t in (("geolod", "geolod:"), ("strat", "strat:"), ("an", "an:"))
                                  if any(md.ns_key(n) == k for n in parent)])
    legend(f, f.h - 70, items, note)
    f.save()
    return f


# ------------------------------------------------------------------ relations

def relations_fig(M: md.Model, outdir: Path, name: str, title: str, mods: tuple[str, ...], note: str) -> tuple[Fig, list[str]]:
    """Object properties with a domain and a range, as arrows. Returns the figure and the properties left out."""
    props = [p for p in M.props_of(*mods) if p.kind == "object" and p.domains and p.ranges]
    left_out = [p.curie for p in M.props_of(*mods) if p.kind == "object" and not (p.domains and p.ranges)]
    edges = [(d, r, p) for p in props for d in p.domains for r in p.ranges]
    nodes = sorted({n for d, r, _ in edges for n in (d, r)}, key=M.curie)

    out = defaultdict(list)
    for d, r, _ in edges:
        if d != r:
            out[d].append(r)
    state, back = {}, set()

    def dfs(n):
        state[n] = 1
        for m in sorted(set(out[n]), key=M.curie):
            if state.get(m) == 1:
                back.add((n, m))
            elif m not in state:
                dfs(m)
        state[n] = 2

    for n in nodes:
        if n not in state:
            dfs(n)
    preds = defaultdict(list)
    for d, r, _ in edges:
        if d != r and (d, r) not in back:
            preds[r].append(d)
    layer = {}

    def lay(n):
        if n not in layer:
            layer[n] = 1 + max((lay(p) for p in preds[n]), default=-1)
        return layer[n]

    for n in nodes:
        lay(n)
    ncol = max(layer.values()) + 1
    cols = [[n for n in nodes if layer[n] == d] for d in range(ncol)]
    nbrs = defaultdict(set)
    for d, r, _ in edges:
        nbrs[d].add(r)
        nbrs[r].add(d)
    pos = {n: i for c in cols for i, n in enumerate(c)}
    for _ in range(4):
        for c in cols:
            c.sort(key=lambda n: (sum(pos[m] for m in nbrs[n]) / max(len(nbrs[n]), 1), M.curie(n)))
            for i, n in enumerate(c):
                pos[n] = i

    def lab(n):
        return M.curie(n) if not md.ns_key(n) or md.ns_key(n) != "geolod" else M.curie(n).split(":", 1)[1]

    colw = [min(360, max(tw(lab(n), 19, True) + 30 for n in c)) for c in cols]
    gap = (1750 - 100 - math.fsum(colw)) / max(ncol - 1, 1) if ncol > 1 else 0
    if ncol > 1 and gap < 110:
        raise ValueError(f"{name}: {ncol} columns leave only {gap:.0f} px between them")
    xs = [50 + math.fsum(colw[:d]) + gap * d for d in range(ncol)]
    pitch, bh, top = 86, 40, 50
    height = int(top + max(len(c) for c in cols) * pitch + 90)
    f = Fig(name, title, 1750, height, outdir)
    box, cy = {}, {}
    for d, c in enumerate(cols):
        block = len(c) * pitch
        y0 = top + (height - 90 - top - block) / 2
        for i, n in enumerate(c):
            cy[n] = y0 + i * pitch + pitch / 2
            box[n] = (xs[d], cy[n] - bh / 2, colw[d], bh)
    pair = defaultdict(list)
    for d, r, p in edges:
        pair[(d, r)].append(p)
    labels = []
    for (d, r), ps in sorted(pair.items(), key=lambda kv: (M.curie(kv[0][0]), M.curie(kv[0][1]))):
        for k, p in enumerate(ps):
            off = (k - (len(ps) - 1) / 2) * 20
            x1, y1, w1, h1 = box[d]
            x2, y2, w2, h2 = box[r]
            if d == r:
                f.path(f"M {x1 + w1 * .25:.1f} {y1} C {x1 + w1 * .25:.1f} {y1 - 50 - 22 * k:.1f} {x1 + w1 * .75:.1f} {y1 - 50 - 22 * k:.1f} {x1 + w1 * .75:.1f} {y1 - 2}", "a")
                labels.append((x1 + w1 / 2, y1 - 50 - 22 * k + 6, p.local))
            elif layer[d] < layer[r]:
                a, b = (x1 + w1, y1 + h1 / 2 + off), (x2 - 2, y2 + h2 / 2 + off)
            elif layer[d] > layer[r]:
                a, b = (x1, y1 + h1 / 2 + off), (x2 + w2 + 2, y2 + h2 / 2 + off)
            else:
                up = y1 > y2
                a, b = (x1 + w1 / 2 + off, y1 if up else y1 + h1), (x2 + w2 / 2 + off, y2 + h2 + 2 if up else y2 - 2)
            if d != r:
                f.line(a[0], a[1], b[0], b[1], "a")
                # the label sits in the first gap after the source column, so a long edge cannot hide it behind a box
                if layer[d] != layer[r] and ncol > 1:
                    lx = a[0] + (gap / 2 if layer[d] < layer[r] else -gap / 2)
                    ly = a[1] + (b[1] - a[1]) * (lx - a[0]) / (b[0] - a[0])
                else:
                    lx, ly = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                labels.append((lx, ly, p.local))
    for n, (x, y, w, h) in box.items():
        nbox(f, x, y, w, h, lab(n), fill_of(n), dash=md.ns_key(n) is None and False)
    for x, y, t in labels:
        B.label(f, x, y, fit(t, 16, 250, True))
    items = family_items(nodes, [(k, t) for k, t in (("geolod", "geolod:"), ("strat", "strat:"), ("an", "an:"))
                                 if any(md.ns_key(n) == k for n in nodes)])
    legend(f, f.h - 70, items, note)
    f.save()
    return f, left_out


# ------------------------------------------------------------------ CRM coverage

def coverage_fig(M: md.Model, outdir: Path, name: str, title: str) -> Fig:
    cards = defaultdict(list)
    loose = []
    for c in sorted(M.classes.values(), key=lambda c: c.curie):
        found, chain = M.anchors(c.iri)
        if not found:
            loose.append(c)
            continue
        via = (M.curie(chain[1]).replace("geolod:", "") if len(chain) > 2 else None)
        for a in found:
            cards[a].append((c, via, len(found) - 1))
    order = sorted(cards, key=lambda a: (FAM_ORDER[md.family(a)], -len(cards[a]), M.curie(a)))
    heads = [(a, M.curie(a), cards[a]) for a in order]
    if loose:
        heads.append((None, "no CRM-family ancestor", [(c, None, 0) for c in loose]))
    cw, gap, line, head, pad = 530, 30, 27, 44, 14
    colh = [0, 0, 0]
    place = []
    for a, t, items in heads:
        h = head + len(items) * line + pad
        k = colh.index(min(colh))
        place.append((a, t, items, 50 + k * (cw + gap), 40 + colh[k], h))
        colh[k] += h + 22
    height = int(40 + max(colh) + 100)
    f = Fig(name, title, 1750, height, outdir)
    for a, t, items, x, y, h in place:
        f.raw(f'<rect x="{x}" y="{y}" width="{cw}" height="{h}" rx="10" fill="#ffffff" stroke="{BLACK}" stroke-width="1.2"/>')
        f.raw(f'<path d="M {x} {y + head} V {y + 10} Q {x} {y} {x + 10} {y} H {x + cw - 10} Q {x + cw} {y} {x + cw} {y + 10} V {y + head} Z" '
              f'fill="{FAM_FILL[md.family(a)] if a else "#ffffff"}" stroke="{BLACK}" stroke-width="1.2"/>')
        f.text(x + 16, y + head / 2, t, 21, True, anchor="start", maxw=cw - 100)
        f.text(x + cw - 14, y + head / 2, f"{len(items)}", 19, False, MUTED, "end")
        for i, (c, via, more) in enumerate(items):
            yy = y + head + i * line + line / 2 + 4
            f.rect(x + 16, yy - 8, 16, 16, OWN_FILL[c.ns], BLACK, 3, 1)
            nm = c.local if c.ns == "geolod" else c.curie
            f.text(x + 42, yy, nm, 18, True, anchor="start", maxw=cw - 60)
            extra = fit((f"via {via}" if via else "direct") + (f"  +{more}" if more else ""), 16,
                        cw - 14 - 42 - tw(nm, 18, True) - 14)
            f.text(x + cw - 14, yy, extra, 16, False, MUTED, "end")
    legend(f, f.h - 70, [(OWN_FILL[k], t) for k, t in (("geolod", "geolod:"), ("strat", "strat:"), ("an", "an:"))],
           "Anchor classes at the top of each card; a class with two nearest anchors appears under both (+n). \"via\" names the first step of the chain.")
    f.save()
    return f


# ------------------------------------------------------------------ crosswalk

def crosswalk_fig(M: md.Model, outdir: Path, name: str, title: str, items: list[str], note: str,
                  extra: dict[str, str] | None = None) -> Fig:
    """Each class in `items` as a row on the left; arrows follow rdfs:subClassOf through the classes of other vocabularies
    that carry it (SOSA, PROV, SKOS ...) to the CIDOC CRM family class it reaches. Own classes that a chain passes on
    the way (LithologicalUnit -> StratigraphicUnit) are not drawn as steps; the left box says "via". A class with no chain
    gets a dashed box in a last row, so a gap shows in the figure and not only in a report."""
    extra = extra or {}
    rows = []
    for iri in items:
        _, chain = M.anchors(iri)
        mids = [n for n in chain[1:-1] if not md.ns_key(n)]
        own_via = [n for n in chain[1:-1] if md.ns_key(n)]
        rows.append((iri, chain[-1] if chain else None, mids, own_via))
    rows.sort(key=lambda r: (r[1] is None, FAM_ORDER[md.family(r[1])] if r[1] else 9, M.curie(r[1]) if r[1] else "",
                             tuple(M.curie(m) for m in r[2]), M.curie(r[0])))
    K = max([len(r[2]) for r in rows] + [0])
    colw = [520] + [330] * K + [400]
    ncol = len(colw)
    gap = (1750 - 100 - math.fsum(colw)) / max(ncol - 1, 1)
    xs = [50 + math.fsum(colw[:i]) + gap * i for i in range(ncol)]
    bh, step = 34, 42
    # left column
    y_left = {r[0]: 40 + i * step for i, r in enumerate(rows)}
    nodes = {}                                   # (iri, column) -> [y values of the rows it serves]
    for iri, anchor, mids, _ in rows:
        cy = y_left[iri] + bh / 2
        if anchor is None:
            continue
        for j, m in enumerate(mids):
            nodes.setdefault((m, K - len(mids) + j + 1), []).append(cy)
        nodes.setdefault((anchor, ncol - 1), []).append(cy)
    pos = {}
    for col in range(1, ncol):
        ks = sorted((k for k in nodes if k[1] == col), key=lambda k: (sum(nodes[k]) / len(nodes[k]), M.curie(k[0])))
        last = -1e9
        for k in ks:
            y = max(sum(nodes[k]) / len(nodes[k]) - bh / 2, last + bh + 8)
            pos[k] = y
            last = y
    loose = [r for r in rows if r[1] is None]
    height = int(max([y_left[r[0]] for r in rows] + list(pos.values()) + [0]) + bh + 130)
    f = Fig(name, title, 1750, height, outdir)
    # edges first, so the boxes sit on top
    drawn = set()
    for iri, anchor, mids, _ in rows:
        if anchor is None:
            continue
        seq = [(iri, 0)] + [(m, K - len(mids) + j + 1) for j, m in enumerate(mids)] + [(anchor, ncol - 1)]
        for a, b in zip(seq, seq[1:]):
            if (a, b) in drawn:
                continue
            drawn.add((a, b))
            ya = (y_left[a[0]] if a[1] == 0 else pos[a]) + bh / 2
            yb = pos[b] + bh / 2
            x1, x2 = xs[a[1]] + colw[a[1]] + 2, xs[b[1]] - 2
            xm = (x1 + x2) / 2
            f.path(f"M {x1:.1f} {ya:.1f} C {xm:.1f} {ya:.1f} {xm:.1f} {yb:.1f} {x2:.1f} {yb:.1f}", "a")
    for iri, anchor, mids, own_via in rows:
        x, y, w = xs[0], y_left[iri], colw[0]
        c = M.classes.get(iri)
        nm = c.local if c and c.ns == "geolod" else (c.curie if c else M.curie(iri))
        fill = fill_of(iri)
        if anchor is None:
            f.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{bh}" rx="8" fill="#fde2e2" stroke="{BLACK}" stroke-width="1.8" stroke-dasharray="7 5"/>')
        else:
            f.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{bh}" rx="8" fill="{fill}" stroke="{BLACK}" stroke-width="1.2"/>')
        side = extra.get(iri) or (("via " + M.curie(own_via[0]).split(":")[-1] + (f" +{len(own_via) - 1}" if len(own_via) > 1 else "")) if own_via else "")
        sw = tw(side, 15) + 14 if side else 0
        f.text(x + 12, y + bh / 2, fit(nm, 18, w - 24 - sw, True), 18, True, anchor="start")
        if side:
            f.text(x + w - 10, y + bh / 2, fit(side, 15, w * 0.55), 15, False, MUTED, "end")
    for (iri, col), y in sorted(pos.items(), key=lambda kv: (kv[0][1], kv[1])):
        nbox(f, xs[col], y, colw[col], bh, M.curie(iri), fill_of(iri), size=18)
    if loose:
        f.text(xs[-1] + colw[-1] / 2, y_left[loose[0][0]] + bh / 2, "no CRM-family ancestor", 18, True, "#7f1d1d")
    own_keys = [(k, t) for k, t in (("geolod", "geolod:"), ("strat", "strat:"), ("an", "an:"))
                if any(md.ns_key(i) == k for i in items)]
    anchors = [r[1] for r in rows if r[1]] + [m for r in rows for m in r[2]]
    legend(f, f.h - 70, family_items(anchors + [i for i in items if not md.ns_key(i)], own_keys), note)
    f.save()
    return f


def crosswalk_e1_fig(M: md.Model, outdir: Path, name: str, title: str, items: list[str], note: str) -> tuple[Fig, list[str]]:
    """The whole way: every class in `items` hangs on its CRM-family anchor, and the anchors are drawn with their
    superclass spine (crm_tree) up to crm:E1_CRM_Entity on the left. Returns the figure and the anchors the spine table lacks."""
    import crm_tree as T
    leaves, missing = defaultdict(list), []
    for iri in items:
        _, chain = M.anchors(iri)
        if chain:
            leaves[chain[-1]].append((iri, [n for n in chain[1:-1]]))
    nodes = set()
    for a in leaves:
        sp = T.up(a)
        nodes.update(sp)
        if sp[-1] != T.E1:
            missing.append(a)
    kids = defaultdict(list)
    for n in nodes:
        if n in T.PARENT and T.PARENT[n] in nodes:
            kids[T.PARENT[n]].append(n)
    roots = sorted(n for n in nodes if n not in T.PARENT or T.PARENT[n] not in nodes)
    depth = {}

    def dep(n, d):
        depth[n] = d
        for k in kids[n]:
            dep(k, d + 1)
    for r in roots:
        dep(r, 0)
    D = max(depth.values()) + 1
    bh, step, cw, lw = 32, 40, 262, 540
    W = 60 + D * (cw + 38) + lw + 40
    ypos, row = {}, [0]

    def place(n):
        ys = []
        for k in sorted(kids[n], key=lambda k: M.curie(k)):
            ys.append(place(k))
        for iri, mids in sorted(leaves.get(n, []), key=lambda l: M.curie(l[0])):
            ypos[("leaf", iri)] = 40 + row[0] * step
            ys.append(ypos[("leaf", iri)])
            row[0] += 1
        if not ys:
            ys = [40 + row[0] * step]
            row[0] += 1
        ypos[n] = sum(ys) / len(ys)
        return ypos[n]
    for r in roots:
        place(r)
    height = 40 + row[0] * step + 130
    f = Fig(name, title, W, height, outdir)
    xs = lambda d: 40 + d * (cw + 38)
    xl = 40 + D * (cw + 38)
    for n in sorted(nodes):
        if n in T.PARENT and T.PARENT[n] in nodes:
            p_ = T.PARENT[n]
            x1, x2, ya, yb = xs(depth[p_]) + cw + 2, xs(depth[n]) - 2, ypos[p_] + bh / 2, ypos[n] + bh / 2
            xm = (x1 + x2) / 2
            f.path(f"M {x1:.1f} {ya:.1f} C {xm:.1f} {ya:.1f} {xm:.1f} {yb:.1f} {x2:.1f} {yb:.1f}", "a")
    for a, ls in leaves.items():
        for iri, _ in ls:
            x1, x2, ya, yb = xs(depth[a]) + cw + 2, xl - 2, ypos[a] + bh / 2, ypos[("leaf", iri)] + bh / 2
            xm = (x1 + x2) / 2
            f.path(f"M {x1:.1f} {ya:.1f} C {xm:.1f} {ya:.1f} {xm:.1f} {yb:.1f} {x2:.1f} {yb:.1f}", "a")
    for n in sorted(nodes, key=lambda n: (depth[n], ypos[n])):
        label = M.curie(n).split(":")[-1].replace("_", " ")
        nbox(f, xs(depth[n]), ypos[n], cw, bh, label, fill_of(n), size=15)
    for a, ls in leaves.items():
        for iri, mids in ls:
            c = M.classes.get(iri)
            nm = c.curie if c else M.curie(iri)
            via = ("via " + ", ".join(M.curie(m) for m in mids)) if mids else ""
            y = ypos[("leaf", iri)]
            f.raw(f'<rect x="{xl}" y="{y}" width="{lw}" height="{bh}" rx="8" fill="{fill_of(iri)}" stroke="{BLACK}" stroke-width="1.2"/>')
            sw = tw(via, 13) + 12 if via else 0
            f.text(xl + 10, y + bh / 2, fit(nm, 16, lw - 20 - sw, True), 16, True, anchor="start")
            if via:
                f.text(xl + lw - 8, y + bh / 2, fit(via, 13, lw * 0.5), 13, False, MUTED, "end")
    own_keys = [(k, t_) for k, t_ in (("geolod", "geolod:"), ("strat", "strat:"), ("an", "an:"))
                if any(md.ns_key(i) == k for i in items)]
    legend(f, f.h - 70, family_items(sorted(nodes) + [i for i in items if not md.ns_key(i)], own_keys), note)
    f.save()
    return f, sorted(missing)


# ------------------------------------------------------------------ instances

LABEL_PREDS = (RDFS.label, SKOS.prefLabel, DCTERMS.title)
ROWS = 9
HIDE_ATTR = {str(p) for p in (RDFS.label, SKOS.prefLabel, DCTERMS.title, RDFS.comment, SKOS.scopeNote, SKOS.note,
                              DCTERMS.identifier, OWL.versionInfo)}


def short(g: Graph, iri) -> str:
    try:
        pfx, ns, local = g.namespace_manager.compute_qname(str(iri), generate=False)
        return f"{pfx}:{local}"
    except Exception:                                   # noqa: BLE001  (no prefix bound)
        s = str(iri).rstrip("/")
        return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1] or s


def is_leaf(g: Graph, iri) -> bool:
    """A resource the graph says nothing about: a unit, a licence, an ORCID. Shown as a row of its neighbour, not as a box."""
    return not any(True for _ in g.predicate_objects(iri))


class _Node:
    def __init__(self, g, M, iri, closure, skip_p=()):
        self.iri = iri
        labels = sorted(str(o) for p in LABEL_PREDS for o in g.objects(iri, p) if isinstance(o, Literal))
        self.head = " ".join(labels[0].split()) if labels else short(g, iri)
        self.curie = short(g, iri)
        self.types = [t for t in sorted(g.objects(iri, RDF.type), key=str) if isinstance(t, URIRef) and t != OWL.NamedIndividual]
        self.attrs = [(short(g, p), str(o)) for p, o in sorted(g.predicate_objects(iri), key=lambda t: (str(t[0]), str(t[1])))
                      if isinstance(o, Literal) and str(p) not in HIDE_ATTR]
        self.attrs += [(short(g, p) + " →", short(g, o)) for p, o in sorted(g.predicate_objects(iri), key=lambda t: (str(t[0]), str(t[1])))
                       if isinstance(o, URIRef) and str(p) not in skip_p and is_leaf(g, o)]
        anc = set()
        for t in self.types:
            anc |= closure(str(t))
        self.kind = ("term" if anc & {"http://www.w3.org/2004/02/skos/core#Concept", "http://www.cidoc-crm.org/cidoc-crm/E55_Type"}
                     else "real" if anc & {"http://w3id.org/geo-lod/SamplingLocation", "http://w3id.org/geo-lod/PalaeoclimateSample",
                                           "http://w3id.org/geo-lod/strat/Core"} else "inst")


def instance_fig(M: md.Model, g: Graph, outdir: Path, name: str, title: str, root: str, skip=(), inbound=(),
                 max_children=9, note="") -> tuple[Fig, list[str]]:
    """One resource and its neighbours two steps out, as stored. Returns the figure and the IRIs it shows."""
    skip_p = {str(RDF.type)} | {str(s) for s in skip}
    cache = {}

    def closure(iri):
        if iri not in cache:
            seen, stack = set(), [iri]
            while stack:
                n = stack.pop()
                for p in M.parents(n):
                    if p not in seen:
                        seen.add(p)
                        stack.append(p)
            cache[iri] = seen | {iri}
        return cache[iri]

    root_u = URIRef(root)
    level = {root_u: 0}
    order = [[root_u], [], []]
    links = []                                         # (s, p, o)

    def neighbours(n):
        out = [(p, o, False) for p, o in sorted(g.predicate_objects(n), key=lambda t: (str(t[0]), str(t[1])))
               if isinstance(o, URIRef) and str(p) not in skip_p and not is_leaf(g, o)]
        if n == root_u:
            out += [(p, s, True) for p in map(URIRef, inbound) for s in sorted(g.subjects(p, n), key=str)]
        return out[:max_children + (3 if n == root_u else 0)]

    for lv in (1, 2):
        for n in list(order[lv - 1]):
            for p, o, rev in neighbours(n):
                if o not in level:
                    level[o] = lv
                    order[lv].append(o)
                if level[o] in (lv, lv - 1) or True:
                    links.append((o, p, n) if rev else (n, p, o))
    nodes = {n: _Node(g, M, n, closure, skip_p) for n in level}
    size = 17
    colw = []
    for lv in range(3):
        ws = []
        for n in order[lv]:
            nd = nodes[n]
            ws += [tw(nd.head, 20, True), tw(nd.curie, size), *[tw(f"{a}  {v}", size) for a, v in nd.attrs[:ROWS]],
                   *[tw(M.curie(str(t)) if M.curie(str(t)) != str(t) else short(g, t), 16) + 20 for t in nd.types[:2]]]
        colw.append(min(430, max(ws, default=200) + 36))
    gap = (1750 - 100 - math.fsum(colw)) / 2
    if gap < 120:
        raise ValueError(f"{name}: columns too wide ({colw})")
    xs = [50, 50 + colw[0] + gap, 50 + colw[0] + colw[1] + 2 * gap]

    def height(n):
        nd = nodes[n]
        return 14 + 28 + 22 + (26 if nd.types else 0) + min(len(nd.attrs), ROWS) * 23 + 12

    ycen, bottom = {}, 0
    for lv in (1, 2):
        cur = 40
        want = sorted(order[lv], key=lambda n: (ycen.get(next((a for a, p, b in links if b == n and a in ycen), None), 0), str(n))) \
            if lv == 2 else order[lv]
        for n in want:
            h = height(n)
            target = None
            if lv == 2:
                src = [a for a, p, b in links if b == n and level.get(a) == 1] + [b for a, p, b in links if a == n and level.get(b) == 1]
                target = ycen[src[0]] - h / 2 if src else None
            y = max(cur, target if target is not None else cur)
            ycen[n] = y + h / 2
            cur = y + h + 22
            bottom = max(bottom, cur)
    ycen[root_u] = (40 + max(bottom, 40 + height(root_u))) / 2 if order[1] else 40 + height(root_u) / 2
    bottom = max(bottom, ycen[root_u] + height(root_u) / 2 + 22)
    f = Fig(name, title, 1750, int(bottom + 110), outdir)
    X = {n: xs[level[n]] for n in level}
    W = {n: colw[level[n]] for n in level}
    shown = set(level)
    skipped = 0
    labels = []
    for s, p, o in links:
        if s not in shown or o not in shown:
            continue
        ls, lo = level[s], level[o]
        if abs(ls - lo) > 1:
            skipped += 1
            continue
        if ls == lo:
            xr = X[s] + W[s]
            f.path(f"M {xr:.1f} {ycen[s]:.1f} L {xr + 34:.1f} {ycen[s]:.1f} L {xr + 34:.1f} {ycen[o]:.1f} L {xr + 2:.1f} {ycen[o]:.1f}", "a")
            labels.append((xr + 34, (ycen[s] + ycen[o]) / 2, short(g, p)))
            continue
        a, b = (s, o) if ls < lo else (o, s)
        x1, y1 = X[a] + W[a], ycen[a]
        x2, y2 = X[b], ycen[b]
        if ls < lo:
            f.line(x1, y1, x2 - 2, y2, "a")
        else:
            f.line(x2, y2, x1 + 2, y1, "a")
        labels.append((x1 + (x2 - x1) * .66, y1 + (y2 - y1) * .66, short(g, p)))
    for n in level:
        nd, h = nodes[n], height(n)
        x, y, w = X[n], ycen[n] - h / 2, W[n]
        st = {"term": TERM, "real": REAL, "inst": INST}[nd.kind]
        f.raw(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="{st[0]}" stroke="{BLACK}" stroke-width="1.2"/>')
        yy = y + 14 + 14
        f.text(x + w / 2, yy, fit(nd.head, 20, w - 20, True), 20, True, st[2], maxw=w - 14)
        f.text(x + w / 2, yy + 24, fit(nd.curie, size, w - 20), size, False, st[2], maxw=w - 14)
        yy += 24 + 22
        if nd.types:
            tt = " + ".join(M.curie(str(t)) if M.curie(str(t)) != str(t) else short(g, t) for t in nd.types[:2])
            tt = fit(tt, 16, w - 36)
            tw_ = tw(tt, 16) + 18
            f.rect(x + w / 2 - tw_ / 2, yy - 12, tw_, 24, CLS[0], BLACK, 12, 1)
            f.text(x + w / 2, yy, tt, 16, False, CLS[2])
            yy += 26
        for a, v in nd.attrs[:ROWS]:
            f.text(x + 14, yy + 4, fit(f"{a}  {v}", size, w - 26), size, False, st[2], "start")
            yy += 23
    for x, y, t in labels:
        B.label(f, x, y, fit(t, 16, 240, True))
    f.legend(f.h - 66, [(INST, "resource"), (REAL, "real object"), (TERM, "term"), (CLS, "class of the resource")])
    cap = note + (f" {skipped} link between non-adjacent columns not drawn." if skipped else "")
    f.text(50, f.h - 22, cap.strip(), 18, color=MUTED, anchor="start", maxw=1650)
    f.save()
    return f, sorted(str(n) for n in level)
