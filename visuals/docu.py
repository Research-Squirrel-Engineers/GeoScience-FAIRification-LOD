#!/usr/bin/env python3
"""docu.py - the documentation pages of geo-lod (docu/), generated from the ontology files and the RDF graphs.

    docu/index.html          overview with the counts read from the ontology
    docu/model.html          class hierarchies and relations per module, class and property tables
    docu/crm-coverage.html   which own classes reach the CIDOC CRM family, and through which chain
    docu/instances.html      one resource per strand with its neighbours, as stored
    docu/sparql.html         eight queries run in the browser (visuals/queries.yaml)

Run it through `py main.py --visuals-only` or `py visuals/build.py --only docu`. The output is deterministic: no date,
sorted iteration, LF line endings. Publishing is done by .github/workflows/docu-pages.yml (gh-pages, /docu/).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import model_data as md  # noqa: E402
import model_figs as F  # noqa: E402
import site_kit as K  # noqa: E402
import sparql_page  # noqa: E402
from rdflib import Graph  # noqa: E402

DOCU = REPO / "docu"
IMG = DOCU / "img"
esc = K.esc
CREDIT = "Fiona Schenk, Florian Thiery, Research Squirrel Engineers at LEIZA. CC BY 4.0."

GROUPS = [("geolod", "geolod: core, EPICA and SISAL", ("core", "epica", "sisal")),
          ("strat", "strat:", ("strat",)),
          ("an", "an:", ("an",))]
D = "http://purl.org/dc/terms/"
INSTANCES = [
    ("i-epica", "EPICA: one methane observation", ["EPICA/rdf/epica_dome_c.ttl"], "http://w3id.org/geo-lod/epica/obs_ch4_0371",
     dict(inbound=["http://www.opengis.net/ont/geosparql#hasGeometry"]),
     "An ice-core observation with its time position, MIS membership, sample, data source and the real objects it speaks about."),
    ("i-sisal", "SISAL: one age control point", ["SISAL/rdf/sisal_v3_dating.ttl", "SISAL/rdf/sisal_sites.ttl"],
     "http://w3id.org/geo-lod/sisal/datingpoint_000942", {},
     "A dating point of a speleothem entity, the dating method and the age models that use it."),
    ("i-ci", "CI: one findspot", ["CI/rdf/ci_findspots.ttl"], "http://w3id.org/geo-lod/ci/cisite_19",
     dict(skip=[D + "creator", D + "rightsHolder", D + "license", "http://www.w3.org/ns/prov#wasAttributedTo",
                "http://www.w3.org/ns/prov#wasDerivedFrom"]),
     "A Campanian Ignimbrite findspot with its geometry and the generating activity; attribution links are left out."),
]


def pill(ns: str) -> str:
    fill = {"geolod": F.GL[0], "strat": F.ST[0], "an": F.AN[0]}[ns]
    return f'<span class="pill" style="background:{fill}">{ns}:</span>'


def class_table(M: md.Model, mods) -> str:
    rows = []
    for c in M.classes_of(*mods):
        anchors, chain = M.anchors(c.iri)
        a = ", ".join(M.curie(x) for x in anchors) if anchors else "none"
        rows.append(f'<tr><td><code>{esc(c.curie)}</code>{"<small>also in " + esc(", ".join(m for m in c.modules[1:])) + "</small>" if len(c.modules) > 1 else ""}</td>'
                    f'<td>{esc(c.label)}</td><td>{esc(c.comment)}</td><td>{esc(a)}</td></tr>')
    return ('<div class="tbl"><table><thead><tr><th>Class</th><th>Label</th><th>Comment</th><th>CRM anchor</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def prop_table(M: md.Model, mods) -> str:
    rows = []
    for p in M.props_of(*mods):
        dom = ", ".join(M.curie(x) for x in p.domains) or "–"
        rng = ", ".join(M.curie(x) for x in p.ranges) or "–"
        rows.append(f'<tr><td><code>{esc(p.curie)}</code><small>{p.kind}</small></td><td>{esc(dom)}</td><td>{esc(rng)}</td>'
                    f'<td>{esc(p.comment) if p.comment else "<span class=\"timing\">no comment</span>"}</td></tr>')
    return ('<div class="tbl"><table><thead><tr><th>Property</th><th>Domain</th><th>Range</th><th>Comment</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def build_model(M: md.Model) -> list[str]:
    figs, body, notes = [], [], []
    for key, title, mods in GROUPS:
        h = F.hierarchy_fig(M, IMG, f"hierarchy-{key}", f"Class hierarchy: {title}", mods,
                            "Own classes solid, CRM-family ancestors dashed; colour shows the family.")
        r, left = F.relations_fig(M, IMG, f"relations-{key}", f"Object properties: {title}", mods,
                                  "Arrows run from domain to range; datatype properties are in the table.")
        body.append(f"<h2>{esc(title)}</h2>")
        body.append(K.fig_card(IMG, f"hierarchy-{key}", "", f"Class hierarchy, {title}", CREDIT))
        body.append(K.fig_card(IMG, f"relations-{key}", "", f"Object properties, {title}", CREDIT))
        if left:
            notes.append(f"{title}: {len(left)} properties are not drawn (domain or range outside the module): "
                         + ", ".join(left))
        body.append(f'<section class="text"><h3>Classes</h3>{class_table(M, mods)}<h3>Properties</h3>{prop_table(M, mods)}</section>')
    unc = M.uncommented()
    if unc:
        body.append(f'<section class="text"><h3>Properties without an rdfs:comment</h3><p>{len(unc)} of {len(M.props)} properties: '
                    + ", ".join(f"<code>{esc(p.curie)}</code>" for p in unc) + "</p></section>")
    if notes:
        body.append('<blockquote>' + "".join(f"<p>{esc(n)}</p>" for n in notes) + "</blockquote>")
    intro = ("Classes, properties, domains and ranges are read from the ontology files when this page is built: "
             "<code>ontology/geo_lod_core.ttl</code>, the EPICA and SISAL extensions, <code>ontology/strat.ttl</code> and "
             "<code>ontology/analysis_core.ttl</code>.")
    K.write_page(DOCU / "model.html", K.page("docu", "model.html", "Data model", intro, "\n".join(body)))
    return notes


def build_coverage(M: md.Model) -> None:
    F.coverage_fig(M, IMG, "crm-coverage", "Own classes and their CIDOC CRM anchors")
    cnt = M.counts()
    stats = "".join(f"<div><b>{cnt[k]['anchored']} / {cnt[k]['classes']}</b><span>{k}: classes with a CRM-family ancestor</span></div>"
                    for k in ("geolod", "strat", "an"))
    loose = [c for c in M.classes.values() if c.ns != "geolod" and not M.anchors(c.iri)[0]]
    rows = "".join(f"<tr><td><code>{esc(c.curie)}</code></td><td>{esc(' → '.join(M.curie(x) for x in M.anchors(c.iri)[1]) or '–')}</td></tr>"
                   for c in sorted(M.classes.values(), key=lambda c: c.curie) if M.anchors(c.iri)[0])
    note = ""
    if loose:
        note = ("<blockquote><p>The N4O rule is hard for <code>geolod:</code> and checked by the build. Not yet anchored in "
                + "strat: and an: (no chain through the bridging file): "
                + ", ".join(f"<code>{esc(c.curie)}</code>" for c in sorted(loose, key=lambda c: c.curie)) + ".</p></blockquote>")
    body = (f'<div class="stat">{stats}</div>' + K.fig_card(IMG, "crm-coverage", "", "Own classes by their nearest CRM-family anchor", CREDIT)
            + note + f'<section class="text"><h3>Chains</h3><div class="tbl"><table><thead><tr><th>Class</th><th>Chain to the CRM family</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
    intro = ("A class counts as anchored when a chain of <code>rdfs:subClassOf</code> axioms, including "
             "<code>ontology/crm_bridging.ttl</code>, reaches CIDOC CRM, CRMsci, CRMgeo or CRMarchaeo.")
    K.write_page(DOCU / "crm-coverage.html", K.page("docu", "crm-coverage.html", "CRM coverage", intro, body))


def build_instances(M: md.Model) -> None:
    cards = []
    for name, title, files, root, kw, caption in INSTANCES:
        g = Graph()
        for f in files:
            g.parse(REPO / f, format="turtle")
        F.instance_fig(M, g, IMG, name, title, root, note=caption, **kw)
        cards.append(K.fig_card(IMG, name, "", title, CREDIT))
    intro = ("One resource per strand with its neighbours two steps out, as stored in the graph. Grey: resources, green: "
             "real objects, violet: terms, brown pill: the class of the resource.")
    K.write_page(DOCU / "instances.html", K.page("docu", "instances.html", "Instance models", intro, "\n".join(cards)))


def build_index(M: md.Model) -> None:
    cnt = M.counts()
    stats = "".join(f"<div><b>{cnt[k]['classes']}</b><span>{k}: classes, {cnt[k]['object']} object and {cnt[k]['datatype']} datatype properties</span></div>"
                    for k in ("geolod", "strat", "an"))
    links = [("model.html", "Data model", "Class hierarchies, relations and tables per module."),
             ("crm-coverage.html", "CRM coverage", "Which classes reach the CIDOC CRM family, and how."),
             ("instances.html", "Instance models", "One EPICA, SISAL and CI resource with its neighbours."),
             ("sparql.html", "Query", "Eight queries over a sample graph, run in the browser."),
             ("../visuals/index.html", "Slide figures", "The twelve figures of the CHNT31 talk.")]
    body = (f'<div class="stat">{stats}</div><section class="text"><ul>'
            + "".join(f'<li><a href="{h}">{esc(t)}</a>: {esc(d)}</li>' for h, t, d in links) + "</ul></section>")
    intro = ("Documentation of the geo-lod data model for ice cores (EPICA), speleothems (SISAL) and the Campanian Ignimbrite "
             "(CI). The pages are generated from the ontology files and the RDF graphs of this repository.")
    K.write_page(DOCU / "index.html", K.page("docu", "index.html", "geo-lod documentation", intro, body))


def main() -> int:
    M = md.Model()
    problems = M.check()
    if problems:
        print("The ontology no longer agrees with the figures:\n  " + "\n  ".join(problems))
        return 1
    IMG.mkdir(parents=True, exist_ok=True)
    K.write_assets(DOCU)
    build_model(M)
    build_coverage(M)
    build_instances(M)
    build_index(M)
    n = sparql_page.build(DOCU)
    print(f"docu/: 5 pages, {len(list(IMG.glob('*.png')))} figures, {n} queries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
