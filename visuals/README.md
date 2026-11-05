# Slide figures and documentation

Twelve figures for the semantic-modelling section of the CHNT31 talk, with a
caption page, and the documentation pages of the data model. Everything is one site and is written to `../docu/`
(`slides.html`, the cluster pages and the documentation pages share one navigation). Everything under `docu/` is generated.

    pip install -r visuals/requirements.txt
    py visuals/build.py              # both
    py visuals/build.py --only docu  # documentation only
    py visuals/build.py --only slides

Published at <https://research-squirrel-engineers.github.io/GeoScience-FAIRification-LOD/docu/>. The ontology pages
of SPARQL Unicorn (the IRI pages) are under `/semweb/`; the root of the site forwards to `docu/`. The third navigation row, "Ontology pages", links into `/semweb/` (overview and the main collections, `SEMWEB_PAGES` in `site_kit.py`); those pages exist only on the `gh-pages` branch, so the links do not work in a local checkout.

Inputs are the repository's own files: `EPICA/rdf/`, `SISAL/rdf/`,
`data/derived/sisal/tables/`, `data/raw/ci/`, `data/curated/`, `data/raw/basemap/`
and `data/raw/wd1/`. The run stops if a value drawn by hand no longer stands in
the graph.

`data/raw/wd1/` holds Table 1 and Table 7 of fionaschenk/wdt-tables, unchanged
(CC BY 4.0, Fiona Schenk). Dashed nodes in figures 06 and 07 are not in the graph;
the WD1 instance IRIs there are illustrative.

Warm and cold stages follow the parity convention of Railsback et al. (2015). The
stalagmite outline in figure 04 is schematic. Colours follow the project's
semantic scheme. SVGs name Fira Sans without embedding it, so open them with the
font installed or use the PNG.

Figures: CC BY 4.0. Code: MIT. Fonts: Fira Sans, SIL OFL 1.1, see `fonts/`.

## Documentation (`docu/`)

| File | Role |
|---|---|
| `model_data.py` | reads classes, properties, domains, ranges and CRM anchors from the ontology files; `check()` stops the build on a mismatch with figures 08 and 12 |
| `model_figs.py` | hierarchy, relations, CRM coverage, crosswalk (per module, other vocabularies, whole way to E1) and instance figures |
| `crm_tree.py` | superclass spine of the CRM-family anchors up to `crm:E1_CRM_Entity`, one primary parent per class; extend it when a bridging axiom reaches a class that is missing (the build says which) |
| `site_kit.py` | stylesheet, navigation and page frame shared by all pages in `docu/` |
| `sample_graph.py` | the graph behind the query page |
| `sparql_page.py`, `queries.yaml` | the query page and its `.rq` files; a query without rows stops the build |
| `docu.py` | writes the six pages; `crosswalk.html` takes every class defined or used and draws its chain to the CRM family. The build fails when a class used in the data has no CRM-family ancestor |

## Cluster pages (`docu/clusters.html`, `docu/cluster-*.html`)

The data model drawn in slices: one page per thematic cluster, so that no figure has to carry all 46 classes of `geolod:`.

    py visuals/build.py --only clusters

| File | Role |
|---|---|
| `clusters.yaml` | which classes belong to which cluster; the build stops when a `geolod:` class is in no cluster or in two, or when a name is not a class. A cluster without `page` is listed as planned |
| `cluster_figs.py` | the cluster graph (members solid, classes of other clusters as dashed edge nodes with the name of their cluster, long arrows routed above the graph) and the data figures, counted from `SISAL/rdf/sisal_v3_dating.ttl` and `data/derived/sisal/tables/` |
| `clusters.py` | writes the overview and one page per cluster that has a `page`; the sentences under the data figures are built from the counts |
| `cluster_mis.py` | the figures of the page "Marine isotope stages", read from `ontology/vocab/mis.ttl`, `EPICA/rdf/epica_dome_c.ttl` and `ontology/trs.ttl`: the two assignment patterns, one stage boundary at its depth on each of the five EPICA timescales, Railsback et al. against LR04, memberships per timescale |

Chronology and age and Marine isotope stages are the first two cluster pages. To add the next one: give it a `page` in `clusters.yaml`, add the file to `CLUSTER_PAGES` in `site_kit.py`, and, if it has data figures, an entry in `DATA` in `clusters.py`.
