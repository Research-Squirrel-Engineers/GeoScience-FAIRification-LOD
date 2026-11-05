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
import cluster_mis as MS  # noqa: E402
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


MPFX = PFX + """PREFIX crm:    <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX time:   <http://www.w3.org/2006/time#>
"""
Q_MEMBER_SHAPE = MPFX + """
# What an observation's stage membership looks like: the nodes of one observation.
SELECT ?assignment ?stage ?scale ?source ?status WHERE {
  ?assignment a geolod:MISMembershipAssignment ;
     crm:P140_assigned_attribute_to <http://w3id.org/geo-lod/epica/obs_ch4_0001> ;
     crm:P141_assigned ?stage ;
     geolod:inChronology ?scale ;
     dct:source ?source ;
     geolod:assignmentStatus ?status .
}"""
Q_DEPTHS = MPFX + """
# The beginning of each stage as a depth, one row per timescale.
# Runs on ontology/vocab/mis.ttl and EPICA/rdf/epica_dome_c.ttl together.
SELECT ?stage ?scale ?depth_m ?age_ka WHERE {
  ?a a geolod:MISAttributeAssignment ;
     crm:P177_assigned_property_of_type geolod:MISBoundaryDepth ;
     crm:P140_assigned_attribute_to ?stage ;
     geolod:inChronology ?scale ;
     crm:P141_assigned/geolod:atDepth_m ?depth_m ;
     prov:wasDerivedFrom/geolod:ageKaBP ?age_ka .
} ORDER BY ?stage ?scale"""
Q_SOURCES = MPFX + """
# The beginning of a stage, as each source dates it, for the stages that have an alternative reading.
SELECT ?stage ?source ?status ?age_ka WHERE {
  ?a a geolod:MISAttributeAssignment ;
     crm:P177_assigned_property_of_type geolod:PeriodBeginning ;
     crm:P140_assigned_attribute_to ?stage ;
     crm:P141_assigned/time:numericPosition ?age_ka ;
     dct:source ?source ;
     geolod:assignmentStatus ?status .
  ?stage a geolod:MarineIsotopeStage .
  FILTER EXISTS {
    ?b a geolod:MISAttributeAssignment ;
       crm:P177_assigned_property_of_type geolod:PeriodBeginning ;
       crm:P140_assigned_attribute_to ?stage ;
       geolod:assignmentStatus geolod:AlternativeAssignment .
  }
} ORDER BY ?stage ?status"""
Q_MEMBERS = MPFX + """
SELECT ?scale (COUNT(?a) AS ?n) WHERE {
  ?a a geolod:MISMembershipAssignment ;
     geolod:inChronology ?scale .
} GROUP BY ?scale ORDER BY DESC(?n)"""
Q_ONE = MPFX + """
# Observations with more than one stage membership. Expected: no row.
SELECT ?obs (COUNT(?a) AS ?n) WHERE {
  ?a a geolod:MISMembershipAssignment ;
     crm:P140_assigned_attribute_to ?obs .
} GROUP BY ?obs HAVING (COUNT(?a) > 1)"""


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


def data_figures_mis(M: md.Model, D: MS.MisData) -> tuple[list[str], list[str]]:
    """Cards for the pattern and the data figures of the MIS page, each with the query that gives its numbers."""
    pattern, data = [], []
    f, st = MS.mis_pattern_fig(M, D, IMG, "cl-mis-pattern")
    pattern.append(K.fig_card(IMG, "cl-mis-pattern", "", "A stage reaches an observation and a depth through geolod:MIS*Assignment", CREDIT))
    n = len(list(D.g.query(Q_MEMBER_SHAPE)))
    if n != 1:
        raise ValueError(f"cl-mis-pattern: the query finds {n} memberships of {st['membership']}, expected one")
    pattern.append(query_block(Q_MEMBER_SHAPE, f"Run on EPICA/rdf/epica_dome_c.ttl: one row, the node on the left of the figure ({st['membership']})."))

    f, st = MS.boundary_depth_fig(D, IMG, "cl-mis-boundary-depths")
    got = sorted((str(r[0]).rsplit("MIS_", 1)[1], str(r[1]).rsplit("/", 1)[1], round(float(r[2]), 3), float(r[3])) for r in D.g.query(Q_DEPTHS))
    want = sorted((str(s), t, round(d, 3), a) for s, t, d, a in st["rows"])
    if got != want:
        raise ValueError("cl-mis-boundary-depths: the query and the figure disagree on the boundary depths")
    data.append(K.fig_card(IMG, "cl-mis-boundary-depths", "", "One stage boundary at its depth on each EPICA timescale", CREDIT))
    data.append(query_block(Q_DEPTHS, f"Run on the two graphs together and compared with the figure: {st['assignments']} rows, "
                            f"{st['boundaries']} boundaries. The widest spread is the beginning of MIS {st['widest']}: {st['spread']:.0f} m between the scales."))

    f, st = MS.stage_sources_fig(D, IMG, "cl-mis-sources")
    got = sorted((int(str(r[0]).rsplit("MIS_", 1)[1]), str(r[1]).rsplit("/", 1)[1], str(r[2]).rsplit("/", 1)[1], float(r[3])) for r in D.g.query(Q_SOURCES))
    want = sorted((n, v[1], status, v[0]) for n, r in D.competing.items() for status, v in r.items() if status != "mode")
    if got != want:
        raise ValueError("cl-mis-sources: the query and the figure disagree on the competing boundaries")
    data.append(K.fig_card(IMG, "cl-mis-sources", "", "The beginning of 28 stages in two sources", CREDIT))
    data.append(query_block(Q_SOURCES, f"Run on ontology/vocab/mis.ttl and compared with the figure: {len(got)} rows, two per stage. "
                            f"{st['within1']} of {st['stages']} boundaries differ by at most one ka; the largest gaps are "
                            + ", ".join(f"MIS {n} ({st['dev'][n]:+.1f} ka)" for n in st["big"]) + "."))

    f, st = MS.memberships_fig(D, IMG, "cl-mis-memberships")
    got = {str(r[0]).rsplit("/", 1)[1]: int(r[1]) for r in D.g.query(Q_MEMBERS)}
    if got != st["counts"] or list(D.g.query(Q_ONE)) or st["total"] != st["observations"]:
        raise ValueError("cl-mis-memberships: the queries and the figure disagree, or an observation has more than one membership")
    data.append(K.fig_card(IMG, "cl-mis-memberships", "", "Stage memberships per timescale", CREDIT))
    data.append(query_block(Q_MEMBERS, f"Run on epica_dome_c.ttl and compared with the figure: {st['total']} memberships. The second query "
                            "(observations with more than one membership) returns no row; the build stops if it does."))
    data.append(query_block(Q_ONE))
    return pattern, data


DATA = {"chronology": (data_figures_chronology, "dating"), "mis": (data_figures_mis, "mis")}


def build_cluster(M: md.Model, clusters: list[dict], cl: dict, sources: dict) -> None:
    C.cluster_graph_fig(M, clusters, cl, IMG, f"cl-{cl['id']}-model")
    body = ["<h2>Model</h2>", K.fig_card(IMG, f"cl-{cl['id']}-model", "", f"Cluster graph: {cl['title']}", CREDIT)]
    if cl["id"] in DATA:
        fn, key = DATA[cl["id"]]
        pattern, data = fn(M, sources[key]())
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
    cache: dict = {}
    # The data are read when a cluster page needs them, and once.
    sources = {"dating": lambda: cache.setdefault("dating", C.Dating()), "mis": lambda: cache.setdefault("mis", MS.MisData())}
    built = 0
    for cl in clusters:
        if cl.get("page"):
            build_cluster(M, clusters, cl, sources)
            built += 1
    build_overview(M, clusters)
    print(f"docu/: {built} cluster pages of {len(clusters)}, overview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
