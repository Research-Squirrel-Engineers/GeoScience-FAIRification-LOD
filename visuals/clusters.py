#!/usr/bin/env python3
"""clusters.py - the cluster pages of geo-lod (docu/): one page per thematic cluster of the data model.

    docu/clusters.html                    overview of the clusters (clusters.yaml)
    docu/cluster-<id>.html                one page: the cluster graph, data figures, the classes of the cluster

A cluster without `page` in clusters.yaml is listed on the overview as planned. Figures are written to docu/img/.
Run it through `py visuals/build.py --only clusters`. The output is deterministic: no date, sorted iteration, LF endings.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cluster_figs as C  # noqa: E402
import model_data as md  # noqa: E402
import site_kit as K  # noqa: E402

SITE = HERE.parent / "docu"
IMG = SITE / "img"
esc = K.esc
CREDIT = "Fiona Schenk, Florian Thiery, Research Squirrel Engineers at LEIZA. CC BY 4.0."


def class_table(M: md.Model, cl: dict) -> str:
    rows = []
    for iri in sorted(cl["iris"], key=M.curie):
        c = M.classes[iri]
        anchors, _ = M.anchors(iri)
        rows.append(f"<tr><td><code>{esc(c.curie)}</code></td><td>{esc(c.label)}</td><td>{esc(c.comment)}</td>"
                    f"<td>{', '.join(f'<code>{esc(M.curie(a))}</code>' for a in anchors)}</td></tr>")
    return ('<div class="tbl"><table><thead><tr><th>Class</th><th>Label</th><th>Comment</th><th>CRM anchor</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


PFX = ("PREFIX geolod: <http://w3id.org/geo-lod/>\nPREFIX strat:  <http://w3id.org/geo-lod/strat/>\n"
       "PREFIX sisal:  <http://w3id.org/geo-lod/sisal/>\n")
Q_HIATUS = PFX + """
SELECT ?model (COUNT(?h) AS ?n) WHERE {
  ?h a geolod:GrowthHiatus ;
     geolod:respectedByAgeModel ?model .
} GROUP BY ?model ORDER BY DESC(?n)"""
Q_POINTS = PFX + """
SELECT ?model (COUNT(?p) AS ?n) WHERE {
  ?p a strat:AgeControlPoint ;
     geolod:usedInAgeModel ?model .
} GROUP BY ?model ORDER BY DESC(?n)"""
Q_ENTITY = PFX + """
SELECT ?point ?depth_mm ?age_ka WHERE {
  ?point a strat:AgeControlPoint ;
         geolod:constrainsSpeleothem sisal:entity_%s ;
         geolod:atDepth_mm ?depth_mm ;
         geolod:ageKaBP ?age_ka .
} ORDER BY ?depth_mm"""
Q_PATTERN = PFX + """
# All ages of one sample, with the model behind each and the one to follow.
# Runs on the full graph SISAL/sisal_rdf.py writes, not on the committed Turtle.
SELECT ?model ?age_ka ?status WHERE {
  ?a a geolod:AgeAssignment ;
     <http://www.cidoc-crm.org/cidoc-crm/P140_assigned_attribute_to> sisal:sample_%s ;
     geolod:ageModel ?model ;
     geolod:ageKaBP ?age_ka ;
     geolod:assignmentStatus ?status .
} ORDER BY ?model"""


def query_block(q: str, note: str = "") -> str:
    """The query as text with a copy button; the note says what it was checked against."""
    q = q.strip("\n")
    n = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<section class="text"><h3>SPARQL</h3><pre>{esc(q)}</pre><div class="row"><span></span>'
            f'<button type="button" data-c="{esc(q)}">Copy</button></div>{n}</section>')


def run_counts(D: C.Dating, q: str) -> dict[str, int]:
    return {str(r[0]).rsplit("AgeModel_", 1)[1]: int(r[1]) for r in D.g.query(q)}


def data_figures_chronology(M: md.Model, D: C.Dating) -> tuple[list[str], list[str]]:
    """Cards for the pattern and the data figures, each with the query that gives its numbers.

    Returns (pattern cards, data cards). The queries are run on the dating graph and compared with what the figure
    counted by itself; a difference stops the build."""
    pattern, data = [], []
    f, st = C.age_pattern_fig(M, D, IMG, "cl-chronology-age-pattern")
    pattern.append(K.fig_card(IMG, "cl-chronology-age-pattern", "", "An age as a property and as geolod:AgeAssignment", CREDIT))
    pattern.append(query_block(Q_PATTERN % int(st["sample"].rsplit("_", 1)[1]),
                               "Not run here: the assignment nodes are in the large graph the pipeline writes, not in the committed Turtle."))

    f, st = C.one_speleothem_fig(D, IMG, "cl-chronology-one-speleothem")
    got = sorted(float(r[2]) for r in D.g.query(Q_ENTITY % "00055"))
    want = sorted(p[2] for p in D.points if p[0] == "55" and p[2] is not None)
    if got != want:
        raise ValueError("cl-chronology-one-speleothem: the query and the figure disagree on the dating points of entity 55")
    data.append(K.fig_card(IMG, "cl-chronology-one-speleothem", "",
                           f"{st['entity']}: the age of every sample under {st['series']} age series", CREDIT))
    sp = st["spread"]
    widest = max(sp, key=sp.get)
    data.append(query_block(Q_ENTITY % "00055", f"Run on sisal_v3_dating.ttl: {len(got)} rows, the circles of the figure. "
                            f"Against StalAge the series differ by up to {sp[widest]:.0f} years ({C.MODEL_NAME.get(widest, widest)})."))

    f, st = C.hiatus_matrix_fig(D, IMG, "cl-chronology-hiatus-matrix")
    if run_counts(D, Q_HIATUS) != st["counts"]:
        raise ValueError("cl-chronology-hiatus-matrix: the query and the figure count different hiatuses per model")
    data.append(K.fig_card(IMG, "cl-chronology-hiatus-matrix", "", "Growth hiatuses and the age models that respected them", CREDIT))
    cn = st["counts"]
    data.append(query_block(Q_HIATUS, f"Run on sisal_v3_dating.ttl and compared with the figure: {st['hiatuses']} hiatuses in "
                            f"{st['entities']} speleothems; " + ", ".join(f"{C.MODEL_NAME.get(m, m)} {cn[m]}" for m in sorted(cn, key=lambda m: -cn[m])) + "."))

    f, st = C.control_points_fig(D, IMG, "cl-chronology-control-points")
    if run_counts(D, Q_POINTS) != st["counts"]:
        raise ValueError("cl-chronology-control-points: the query and the figure count different points per model")
    data.append(K.fig_card(IMG, "cl-chronology-control-points", "", "Dating points used by each age model", CREDIT))
    data.append(query_block(Q_POINTS, f"Run on sisal_v3_dating.ttl and compared with the figure: {st['total']} dating points."))
    return pattern, data


DATA = {"chronology": data_figures_chronology}


def build_cluster(M: md.Model, clusters: list[dict], cl: dict, D: C.Dating | None) -> None:
    C.cluster_graph_fig(M, clusters, cl, IMG, f"cl-{cl['id']}-model")
    body = ["<h2>Model</h2>", K.fig_card(IMG, f"cl-{cl['id']}-model", "", f"Cluster graph: {cl['title']}", CREDIT)]
    if cl["id"] in DATA:
        pattern, data = DATA[cl["id"]](M, D)
        body += ["<h2>Modelling pattern</h2>"] + pattern + ["<h2>In the data</h2>"] + data
    body.append(f'<section class="text"><h3>Classes</h3>{class_table(M, cl)}</section>')
    intro = esc(cl["lead"]) + ' All clusters are on the <a href="clusters.html">overview</a>.'
    K.write_page(SITE / cl["page"], K.page("docu", cl["page"], cl["title"], intro, "\n".join(body)))


def build_overview(M: md.Model, clusters: list[dict]) -> None:
    items = []
    for cl in clusters:
        n = len(cl["iris"])
        name = esc(cl["title"])
        title = f'<a href="{cl["page"]}">{name}</a>' if cl.get("page") else f"{name} <small>(planned)</small>"
        items.append(f"<li><b>{title}</b>: {esc(cl['lead'])} <small>{n} classes</small></li>")
    body = ('<section class="text"><ul>' + "".join(items) + "</ul></section>"
            f'<p class="note">Every geolod: class belongs to exactly one cluster ({sum(1 for c in M.classes.values() if c.ns == "geolod")} classes); '
            "the assignment is <code>visuals/clusters.yaml</code>, and the build stops when a class is missing or listed twice.</p>")
    intro = ('The data model drawn in slices instead of as one graph. Each page shows the classes of one cluster, the relations '
             'that leave it as dashed edge nodes, and figures from the data. The whole model is on the '
             '<a href="model.html">data model page</a>.')
    K.write_page(SITE / "clusters.html", K.page("docu", "clusters.html", "Model clusters", intro, body))


def main() -> int:
    M = md.Model()
    clusters = C.load_clusters(M)
    IMG.mkdir(parents=True, exist_ok=True)
    K.write_assets(SITE)
    D = C.Dating() if any(cl.get("page") and cl["id"] in DATA for cl in clusters) else None
    built = 0
    for cl in clusters:
        if cl.get("page"):
            build_cluster(M, clusters, cl, D)
            built += 1
    build_overview(M, clusters)
    print(f"docu/: {built} cluster pages of {len(clusters)}, overview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
