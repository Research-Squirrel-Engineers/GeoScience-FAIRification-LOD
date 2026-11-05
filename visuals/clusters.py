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
import cluster_archives as AR
import cluster_archaeology as AY
import cluster_measurement as MT  # noqa: E402
import cluster_mis as MS  # noqa: E402
import cluster_sources as SO
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


APFX = PFX + """PREFIX sosa:   <http://www.w3.org/ns/sosa/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct:    <http://purl.org/dc/terms/>
"""
Q_INVENTORY = APFX + """
# Per class of the cluster: nodes typed with the class itself, and nodes typed with it or a subclass.
# Runs on the committed graphs (EPICA, SISAL cave catalogue) together with the three ontology files.
SELECT ?class (SUM(IF(?t = ?class, 1, 0)) AS ?asserted) (COUNT(DISTINCT ?x) AS ?with_subclasses) WHERE {
  VALUES ?class { %s }
  ?x a ?t .
  ?t rdfs:subClassOf* ?class .
} GROUP BY ?class"""
Q_FEATURE = APFX + """
SELECT ?dataset ?feature_class (COUNT(?obs) AS ?n) WHERE {
  ?dataset a geolod:IceCoreDataset ;
           geolod:hasObservation ?obs .
  ?obs sosa:hasFeatureOfInterest ?feature .
  ?feature a ?feature_class .
  FILTER(?feature_class IN (geolod:IceCore, geolod:SampleSection))
} GROUP BY ?dataset ?feature_class ORDER BY ?dataset"""
Q_TILING = APFX + """
# The sections of the core: how many, how thick in all, and where they start and end.
SELECT (COUNT(?s) AS ?sections) (SUM(?bottom - ?top) AS ?thickness_m) (MIN(?top) AS ?from_m) (MAX(?bottom) AS ?to_m) WHERE {
  ?s a geolod:SampleSection ;
     geolod:depthTop_m ?top ;
     geolod:depthBottom_m ?bottom .
}"""
Q_CAVES = APFX + """
SELECT ?cave ?label ?d18o_samples WHERE {
  ?cave a geolod:Cave ;
        rdfs:label ?label ;
        geolod:countD18OSamples ?d18o_samples .
} ORDER BY DESC(?d18o_samples) ?label"""


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


def data_figures_archives(M: md.Model, D: AR.ArcData, cl: dict) -> tuple[list[str], list[str]]:
    """Cards for the pattern and the data figures of the archives page, each with the query that gives its numbers."""
    from rdflib import URIRef
    from rdflib.namespace import RDF, RDFS
    pattern, data = [], []
    f, st = AR.archive_pattern_fig(M, D, IMG, "cl-archives-pattern")
    pattern.append(K.fig_card(IMG, "cl-archives-pattern", "", "A place, the thing taken from it and the part measured", CREDIT))

    # inventory: the query against an independent count in Python
    curies = {iri: M.curie(iri) for iri in cl["iris"]}
    q = Q_INVENTORY % " ".join(sorted(curies.values()))
    got = {M.curie(str(r[0])) if str(r[0]) in M.classes else str(r[0]): (int(r[1]), int(r[2])) for r in D.g.query(q)}
    want = {}
    for iri, cur in curies.items():
        cls = URIRef(iri)
        sub = set(D.g.transitive_subjects(RDFS.subClassOf, cls))
        asserted = {x for x in D.g.subjects(RDF.type, cls)}
        withsub = {x for t in sub for x in D.g.subjects(RDF.type, t)}
        want[cur] = (len(asserted), len(withsub))
    got = {k: v for k, v in got.items()}
    for cur, v in want.items():
        if got.get(cur, (0, 0)) != v:
            raise ValueError(f"cl-archives-inventory: the query gives {got.get(cur, (0, 0))} for {cur}, the count in Python {v}")
    AR.inventory_fig(M, cl["iris"], D, want, IMG, "cl-archives-inventory")
    data.append(K.fig_card(IMG, "cl-archives-inventory", "", "Which classes have nodes in the committed graphs", CREDIT))
    data.append(query_block(q.replace(" ".join(sorted(curies.values())), "\n    ".join(sorted(curies.values()))),
                            f"Run on the committed graphs and compared with a count in Python: {sum(1 for v in want.values() if v[0])} of {len(want)} classes have asserted nodes."))

    f, st = AR.feature_fig(D, IMG, "cl-archives-feature")
    got = {}
    for r in D.g.query(Q_FEATURE):
        got.setdefault(str(r[0]).rsplit("/", 1)[1], {})[str(r[1]).rsplit("/", 1)[1]] = int(r[2])
    if {k: (v.get("IceCore", 0), v.get("SampleSection", 0)) for k, v in got.items()} != st["rows"]:
        raise ValueError("cl-archives-feature: the query and the figure disagree on the feature of interest")
    row = next(iter(D.g.query(Q_TILING)))
    if (int(row[0]), round(float(row[1]), 3), float(row[2]), float(row[3])) != (st["sections"], round(st["thickness"], 3), st["top"], st["bottom"]):
        raise ValueError("cl-archives-feature: the tiling query and the figure disagree on the sections")
    data.append(K.fig_card(IMG, "cl-archives-feature", "", "What the observations of each dataset are about", CREDIT))
    data.append(query_block(Q_FEATURE, "Run on epica_dome_c.ttl and compared with the figure: five datasets, two classes."))
    data.append(query_block(Q_TILING, f"Compared with the figure: {st['sections']} sections, {st['thickness']:.1f} m of {st['top']:g} to {st['bottom']:g} m; "
                            + ("the sections tile the core without gap or overlap." if st["tiles"] else "there are gaps or overlaps.")))

    f, st = AR.caves_fig(D, IMG, "cl-archives-caves")
    got = [(str(r[1]), int(r[2])) for r in D.g.query(Q_CAVES)]
    if got != D.caves:
        raise ValueError("cl-archives-caves: the query and the figure disagree on the caves")
    data.append(K.fig_card(IMG, "cl-archives-caves", "", "How many delta-18-O samples each of the 365 caves stands for", CREDIT))
    data.append(query_block(Q_CAVES, f"Run on sisal_sites.ttl and compared with the figure: {st['caves']} rows. {st['total']:,} samples in all, median {st['median']:g}, "
                            f"most {st['max'][1]:,} ({st['max'][0]})."))
    return pattern, data


TPFX = APFX + """PREFIX qudt:   <http://qudt.org/schema/qudt/>
PREFIX epica:  <http://w3id.org/geo-lod/epica/>
"""
Q_OBS_ONE = TPFX + """
# Everything the committed graph says about one observation: the nodes of the pattern figure.
SELECT ?property ?value WHERE {
  epica:obs_ch4_0001 ?property ?value .
} ORDER BY ?property ?value"""
Q_SERIES = TPFX + """
# The methane record: age, measured value and the two smoothed values, one row per observation.
SELECT ?age_ka ?measured ?rolling_median ?savitzky_golay WHERE {
  ?obs sosa:observedProperty epica:property_ch4 ;
       geolod:ageKaBP ?age_ka ;
       geolod:measuredValue ?measured ;
       geolod:smoothedValue_rollingMedian ?rolling_median ;
       geolod:smoothedValue_savgol ?savitzky_golay .
} ORDER BY ?age_ka"""
Q_COVERAGE = TPFX + """
# Per dataset: observations, and how many carry each kind of value.
SELECT ?dataset ?unit (COUNT(DISTINCT ?obs) AS ?observations) (COUNT(?measured) AS ?with_value) (COUNT(?sd) AS ?with_sd)
       (COUNT(?median) AS ?with_median) (COUNT(?savgol) AS ?with_savgol) WHERE {
  ?dataset a geolod:IceCoreDataset ;
           geolod:hasObservation ?obs .
  ?obs qudt:unit ?unit .
  OPTIONAL { ?obs geolod:measuredValue ?measured }
  OPTIONAL { ?obs geolod:standardDeviation ?sd }
  OPTIONAL { ?obs geolod:smoothedValue_rollingMedian ?median }
  OPTIONAL { ?obs geolod:smoothedValue_savgol ?savgol }
} GROUP BY ?dataset ?unit ORDER BY DESC(?observations) ?dataset"""


def data_figures_measurement(M: md.Model, D: MT.MeasData, cl: dict) -> tuple[list[str], list[str]]:
    """Cards for the pattern and the data figures of the measurement page, each with the query that gives its numbers."""
    from rdflib import URIRef
    from rdflib.namespace import RDF, RDFS
    pattern, data = [], []
    f, st = MT.pattern_fig(M, D, IMG, "cl-measurement-pattern")
    rows = list(D.g.query(Q_OBS_ONE))
    if len({str(r[0]) for r in rows}) != st["properties"] + 1:
        raise ValueError("cl-measurement-pattern: the query finds a different number of properties than the figure counts")
    pattern.append(K.fig_card(IMG, "cl-measurement-pattern", "", "One observation in three views", CREDIT))
    pattern.append(query_block(Q_OBS_ONE, f"Run on epica_dome_c.ttl: {len(rows)} statements with {st['properties'] + 1} distinct properties. "
                               f"The figure draws {st['shown']} of them; the others are listed under it."))

    curies = {iri: M.curie(iri) for iri in cl["iris"]}
    q = Q_INVENTORY % " ".join(sorted(curies.values()))
    got = {M.curie(str(r[0])) if str(r[0]) in M.classes else str(r[0]): (int(r[1]), int(r[2])) for r in D.g.query(q)}
    want = {}
    for iri, cur in curies.items():
        cls = URIRef(iri)
        sub = set(D.g.transitive_subjects(RDFS.subClassOf, cls))
        want[cur] = (len({x for x in D.g.subjects(RDF.type, cls)}), len({x for t in sub for x in D.g.subjects(RDF.type, t)}))
    for cur, v in want.items():
        if got.get(cur, (0, 0)) != v:
            raise ValueError(f"cl-measurement-inventory: the query gives {got.get(cur, (0, 0))} for {cur}, the count in Python {v}")
    AR.inventory_fig(M, cl["iris"], D, want, IMG, "cl-measurement-inventory",
                     "0 and 0: the class has no node in the committed Turtle; the SISAL observations and the properties they use are in the large graph of the pipeline.")
    data.append(K.fig_card(IMG, "cl-measurement-inventory", "", "Which classes have nodes in the committed graphs", CREDIT))
    data.append(query_block(q.replace(" ".join(sorted(curies.values())), "\n    ".join(sorted(curies.values()))),
                            f"Run on epica_dome_c.ttl with the ontology files and compared with a count in Python: {sum(1 for v in want.values() if v[0])} of {len(want)} classes have asserted nodes."))

    f, st = MT.coverage_fig(D, IMG, "cl-measurement-coverage")
    got = {}
    for r in D.g.query(Q_COVERAGE):
        got[str(r[0]).rsplit("/", 1)[1]] = (int(r[2]), tuple(int(r[i]) for i in (3, 4, 5, 6)), "unit:" + str(r[1]).rsplit("/", 1)[1])
    if got != st["rows"]:
        raise ValueError("cl-measurement-coverage: the query and the figure disagree on the values per dataset")
    data.append(K.fig_card(IMG, "cl-measurement-coverage", "", "Which kinds of value each dataset carries", CREDIT))
    data.append(query_block(Q_COVERAGE, f"Run on epica_dome_c.ttl and compared with the figure: five datasets, {st['total']:,} observations."))

    f, st = MT.series_fig(D, IMG, "cl-measurement-series")
    got = [(round(float(r[0]), 4), float(r[1]), float(r[2]), float(r[3])) for r in D.g.query(Q_SERIES)]
    if got != st["rows"]:
        raise ValueError("cl-measurement-series: the query and the figure disagree on the methane record")
    data.append(K.fig_card(IMG, "cl-measurement-series", "", "Measured and smoothed methane", CREDIT))
    data.append(query_block(Q_SERIES, f"Run on epica_dome_c.ttl and compared with the figure: {st['n']} rows, {st['first_age']:g} to {st['last_age']:.0f} ka BP."))
    return pattern, data


YPFX = TPFX + """PREFIX geo:    <http://www.opengis.net/ont/geosparql#>
PREFIX ci:     <http://w3id.org/geo-lod/ci/>
PREFIX dcat:   <http://www.w3.org/ns/dcat#>
"""
Q_READING = YPFX + """
# What the graphs say about the three nodes of the pattern figure: a cave read for archaeology, a findspot read, a findspot not read.
SELECT ?site ?property ?value WHERE {
  VALUES ?site { geolod:Cave_site_0077 ci:cisite_43 ci:cisite_1 }
  ?site ?property ?value .
} ORDER BY ?site ?property ?value"""
Q_SCREENING = YPFX + """
# Per kind of place: how many, how many have been screened for archaeology, how many carry archaeological evidence.
SELECT ?kind (COUNT(DISTINCT ?site) AS ?places) (COUNT(DISTINCT ?screened) AS ?screened_places)
       (COUNT(DISTINCT ?positive) AS ?typed_archaeological) (COUNT(DISTINCT ?both) AS ?typed_and_screened) WHERE {
  { ?site a geolod:Cave . BIND("caves" AS ?kind) } UNION { ?site a geolod:CIFindspot . BIND("CI findspots" AS ?kind) }
  OPTIONAL { ?site geolod:screenedForArchaeology true . BIND(?site AS ?screened) }
  OPTIONAL { ?site a ?evidence . FILTER(?evidence IN (geolod:ArchaeologicalCaveSite, geolod:CIArchaeologicalSite)) BIND(?site AS ?positive) }
  BIND(IF(BOUND(?screened) && BOUND(?positive), ?site, ?nothing) AS ?both)
} GROUP BY ?kind ORDER BY ?kind"""
Q_CONTEXT = YPFX + """
SELECT ?kind ?context ?confidence (COUNT(?site) AS ?sites) WHERE {
  ?site geolod:archaeologicalBroaderContext ?context ;
        geolod:archaeologicalConfidence ?confidence .
  BIND(IF(EXISTS { ?site a geolod:CIArchaeologicalSite }, "CI", "cave") AS ?kind)
} GROUP BY ?kind ?context ?confidence ORDER BY ?kind ?context ?confidence"""
Q_FINDSPOTS = YPFX + """
# The findspots of the map: position and the certainty of the position (a statement on the geometry node).
SELECT ?site ?wkt ?certainty WHERE {
  ?site a geolod:CIFindspot ;
        geo:hasGeometry ?geom .
  ?geom geo:asWKT ?wkt .
  OPTIONAL { ?geom geolod:hasCertaintyLevel ?certainty }
} ORDER BY ?site"""
Q_ARCH_CAVES = YPFX + """
SELECT ?cave ?wkt WHERE {
  ?cave a geolod:ArchaeologicalCaveSite ;
        geo:hasGeometry/geo:asWKT ?wkt .
} ORDER BY ?cave"""
SPFX = YPFX
Q_CATALOGUE = SPFX + """
# The catalogue, its datasets, the source each names, and how many observations each dataset has.
SELECT ?dataset ?source (COUNT(?obs) AS ?observations) WHERE {
  ?catalogue a geolod:PalaeoclimateDataCatalogue ;
             dcat:dataset ?dataset .
  ?dataset dct:source ?source ;
           geolod:hasObservation ?obs .
} GROUP BY ?dataset ?source ORDER BY ?dataset"""
Q_CITING = SPFX + """
# How many ice core observations cite each source with prov:wasDerivedFrom.
SELECT ?source (COUNT(?obs) AS ?citing_observations) WHERE {
  ?obs a geolod:IceCoreObservation ;
       prov:wasDerivedFrom ?source .
} GROUP BY ?source ORDER BY ?source"""
Q_DERIVED = SPFX + """
# Which nodes cite which source, counted by class. A source is a typed geolod:DataSource or a node the graph says nothing else about.
SELECT ?source ?typed ?class (COUNT(DISTINCT ?x) AS ?nodes) WHERE {
  { ?x prov:wasDerivedFrom ?source } UNION { ?x dct:source ?source }
  BIND(EXISTS { ?source a geolod:DataSource } AS ?typed)
  FILTER (?typed || NOT EXISTS { ?source ?p ?o })
  ?x a ?class .
  FILTER (STRSTARTS(STR(?class), STR(geolod:)) && ?class != geolod:DataSource)
} GROUP BY ?source ?typed ?class ORDER BY ?source DESC(?nodes) ?class"""

def _inventory(M: md.Model, D, cl: dict, name: str, note: str) -> tuple[str, str]:
    """The inventory card and its query for a cluster page: the query is run and compared with an independent count in Python."""
    from rdflib import URIRef
    from rdflib.namespace import RDF, RDFS
    curies = {iri: M.curie(iri) for iri in cl["iris"]}
    q = Q_INVENTORY % " ".join(sorted(curies.values()))
    got = {M.curie(str(r[0])) if str(r[0]) in M.classes else str(r[0]): (int(r[1]), int(r[2])) for r in D.g.query(q)}
    want = {}
    for iri, cur in curies.items():
        cls = URIRef(iri)
        sub = set(D.g.transitive_subjects(RDFS.subClassOf, cls))
        want[cur] = (len({x for x in D.g.subjects(RDF.type, cls)}), len({x for t in sub for x in D.g.subjects(RDF.type, t)}))
    for cur, v in want.items():
        if got.get(cur, (0, 0)) != v:
            raise ValueError(f"{name}: the query gives {got.get(cur, (0, 0))} for {cur}, the count in Python {v}")
    AR.inventory_fig(M, cl["iris"], D, want, IMG, name, note)
    card = K.fig_card(IMG, name, "", "Which classes have nodes in the committed graphs", CREDIT)
    block = query_block(q.replace(" ".join(sorted(curies.values())), "\n    ".join(sorted(curies.values()))),
                        f"Run on the committed graphs with the ontology files and compared with a count in Python: {sum(1 for v in want.values() if v[0])} of {len(want)} classes have asserted nodes.")
    return card, block


def data_figures_archaeology(M: md.Model, D: AY.ArchData, cl: dict) -> tuple[list[str], list[str]]:
    pattern, data = [], []
    f, st = AY.pattern_fig(M, D, IMG, "cl-archaeology-pattern")
    rows = list(D.g.query(Q_READING))
    pattern.append(K.fig_card(IMG, "cl-archaeology-pattern", "", "One archaeological reading on two kinds of place", CREDIT))
    pattern.append(query_block(Q_READING, f"Run on the committed graphs: {len(rows)} statements about the three nodes of the figure; the rows of each card are among them."))

    f, st = AY.screening_fig(D, IMG, "cl-archaeology-screening")
    got = {str(r[0]): (int(r[1]), int(r[2]), int(r[3]), int(r[4])) for r in D.g.query(Q_SCREENING)}
    if got != {"caves": st["caves"], "CI findspots": st["ci"]}:
        raise ValueError(f"cl-archaeology-screening: the query gives {got}, the figure {st}")
    data.append(K.fig_card(IMG, "cl-archaeology-screening", "", "Looked at, found, not looked at", CREDIT))
    data.append(query_block(Q_SCREENING, f"Run on the committed graphs and compared with the figure: {st['caves'][2]} of {st['caves'][0]} caves and {st['ci'][2]} of {st['ci'][0]} findspots carry an archaeological class; {st['caves'][3]} and {st['ci'][3]} of them also have a curated reading."))

    f, st = AY.context_fig(D, IMG, "cl-archaeology-context")
    got = {f"{r[0]}/{str(r[1]).rsplit('/', 1)[-1]}/{r[2]}": int(r[3]) for r in D.g.query(Q_CONTEXT)}
    if got != st["rows"]:
        raise ValueError("cl-archaeology-context: the query and the figure disagree on contexts and confidence")
    data.append(K.fig_card(IMG, "cl-archaeology-context", "", "Archaeological sites by broader context and confidence", CREDIT))
    data.append(query_block(Q_CONTEXT, f"Run on the committed graphs and compared with the figure: {st['total']} sites."))

    f, st = AY.map_fig(D, IMG, "cl-archaeology-map")
    from rdflib import URIRef
    got = sorted((str(r[0]).rsplit("/", 1)[-1], round(AY._point(r[1])[0], 4), round(AY._point(r[1])[1], 4), str(r[2]).rsplit("/", 1)[-1] if r[2] is not None else "none") for r in D.g.query(Q_FINDSPOTS))
    if got != st["findspots"]:
        raise ValueError("cl-archaeology-map: the query and the figure disagree on the findspots")
    got = sorted((str(r[0]).rsplit("/", 1)[-1], round(AY._point(r[1])[0], 4), round(AY._point(r[1])[1], 4)) for r in D.g.query(Q_ARCH_CAVES))
    if got != st["caves"]:
        raise ValueError("cl-archaeology-map: the query and the figure disagree on the archaeological caves")
    data.append(K.fig_card(IMG, "cl-archaeology-map", "", "Campanian Ignimbrite findspots and archaeological caves", CREDIT))
    data.append(query_block(Q_FINDSPOTS, f"Run on ci_findspots.ttl and compared with the figure: {len(st['findspots'])} findspots; the certainty is read from the geometry node."))
    data.append(query_block(Q_ARCH_CAVES, f"Compared with the figure: {len(st['caves'])} caves, {st['inside']} of them inside the window."))

    card, block = _inventory(M, D, cl, "cl-archaeology-inventory", "0 and 0: the class has no node in the committed Turtle.")
    data += [card, block]
    return pattern, data


def data_figures_sources(M: md.Model, D: SO.SrcData, cl: dict) -> tuple[list[str], list[str]]:
    pattern, data = [], []
    f, st = SO.pattern_fig(M, D, IMG, "cl-sources-pattern")
    citing = {str(r[0]): int(r[1]) for r in D.g.query(Q_CITING)}
    got = {str(r[0]).rsplit("/", 1)[-1]: (int(r[2]), citing.get(str(r[1]), 0)) for r in D.g.query(Q_CATALOGUE)}
    key = st["dataset"].split(":", 1)[1]
    if len(got) != st["datasets"] or got.get(key) != (st["observations"], st["cited"]):
        raise ValueError(f"cl-sources-pattern: the query gives {got}, the figure {st}")
    pattern.append(K.fig_card(IMG, "cl-sources-pattern", "", "From a catalogue to a source", CREDIT))
    pattern.append(query_block(Q_CATALOGUE, f"Run on epica_dome_c.ttl and compared with the figure: {len(got)} datasets; {st['dataset']} has {st['observations']:,} observations."))
    pattern.append(query_block(Q_CITING, f"The second query counts the observations that cite each source; {st['cited']:,} of them cite {st['source']}, as many as the dataset has."))

    f, st = SO.sources_fig(D, IMG, "cl-sources-table")
    got: dict = {}
    for r in D.g.query(Q_DERIVED):
        got.setdefault(str(r[0]).rsplit("/", 1)[-1], [bool(r[1].toPython()), []])[1].append((str(r[2]).rsplit("/", 1)[-1], int(r[3])))
    want = {k: [v[0], sorted(v[1], key=lambda kv: (-kv[1], kv[0]))] for k, v in st["rows"].items()}
    got = {k: [v[0], sorted(v[1], key=lambda kv: (-kv[1], kv[0]))] for k, v in got.items()}
    want = {k: [v[0], sorted(v[1], key=lambda kv: (-kv[1], kv[0]))] for k, v in want.items()}
    if got != want:
        raise ValueError("cl-sources-table: the query and the figure disagree on what derives from which source")
    data.append(K.fig_card(IMG, "cl-sources-table", "", "Which sources the graphs cite", CREDIT))
    data.append(query_block(Q_DERIVED, f"Run on the committed graphs and compared with the figure: {len(got)} sources, {st['typed']} typed and {st['cited']} cited only."))

    card, block = _inventory(M, D, cl, "cl-sources-inventory", "Both classes have nodes in the committed Turtle (the sources and the EPICA catalogue).")
    data += [card, block]
    return pattern, data


DATA = {"chronology": (data_figures_chronology, "dating"), "mis": (data_figures_mis, "mis"), "archives": (data_figures_archives, "archives"),
        "measurement": (data_figures_measurement, "measurement"),
        "archaeology": (data_figures_archaeology, "archaeology"), "sources": (data_figures_sources, "sources")}


def build_cluster(M: md.Model, clusters: list[dict], cl: dict, sources: dict) -> None:
    C.cluster_graph_fig(M, clusters, cl, IMG, f"cl-{cl['id']}-model")
    body = ["<h2>Model</h2>", K.fig_card(IMG, f"cl-{cl['id']}-model", "", f"Cluster graph: {cl['title']}", CREDIT)]
    if cl["id"] in DATA:
        fn, key = DATA[cl["id"]]
        pattern, data = fn(M, sources[key]()) if cl["id"] not in ("archives", "measurement", "archaeology", "sources") else fn(M, sources[key](), cl)
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
    sources = {"dating": lambda: cache.setdefault("dating", C.Dating()), "mis": lambda: cache.setdefault("mis", MS.MisData()),
               "archives": lambda: cache.setdefault("archives", AR.ArcData()),
               "measurement": lambda: cache.setdefault("measurement", MT.MeasData()),
               "archaeology": lambda: cache.setdefault("archaeology", AY.ArchData()),
               "sources": lambda: cache.setdefault("sources", SO.SrcData())}
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
