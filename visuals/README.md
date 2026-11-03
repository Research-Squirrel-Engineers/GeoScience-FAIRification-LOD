# Slide figures

Nine figures for the semantic-modelling section of the CHNT31 talk, with a
caption page. Everything under `site/` is generated.

    pip install -r visuals/requirements.txt
    py visuals/build.py

Published at
<https://research-squirrel-engineers.github.io/GeoScience-FAIRification-LOD/visuals/>.

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
