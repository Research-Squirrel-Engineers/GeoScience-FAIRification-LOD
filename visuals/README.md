# Slide figures and documentation

Twelve figures for the semantic-modelling section of the CHNT31 talk, with a
caption page (`site/`), and the documentation pages of the data model (`../docu/`).
Everything under `site/` and `docu/` is generated.

    pip install -r visuals/requirements.txt
    py visuals/build.py              # both
    py visuals/build.py --only docu  # documentation only
    py visuals/build.py --only slides

Published at
<https://research-squirrel-engineers.github.io/GeoScience-FAIRification-LOD/visuals/> (slides) and
<https://research-squirrel-engineers.github.io/GeoScience-FAIRification-LOD/docu/> (documentation).

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
| `model_figs.py` | hierarchy, relations, CRM coverage and instance figures |
| `site_kit.py` | stylesheet, navigation and page frame shared by `docu/` and `site/` |
| `sample_graph.py` | the graph behind the query page |
| `sparql_page.py`, `queries.yaml` | the query page and its `.rq` files; a query without rows stops the build |
| `docu.py` | writes the five pages |
