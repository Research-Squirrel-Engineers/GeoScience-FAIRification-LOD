# README-RUN.md — what to start with what

Every entry point of the repository, its switches, and what is on disk
afterwards. Meant for looking things up, not for reading from start to finish.

All commands are on **one** line and run from the root directory unless stated
otherwise. Windows notation with `py`; on Linux and macOS use `python3` and
forward slashes.

This file is kept in step with every change to the scripts. If a switch is
missing here, that is a bug and not a secret.

---

## The short way

| I want to … | Command |
|---|---|
| rebuild everything, fast | `py main.py` |
| rebuild everything, completely | `py main.py --sisal-sites all` |
| a release version | `py main.py --bundle-format release` |
| work on the CI strand only | `py main.py --ci-only --archaeo-only --no-bundle` |
| figures for print | `py main.py --sisal-sites all --dpi print` |
| see what was generated | `py clean.py` |

---

## `main.py` — the pipeline

Runs the individual scripts in a fixed order, logs everything to
`pipeline_report.txt` and times every step. The step numbers come from a
counter and follow the run: a full run counts up to 14, a `--ci-only` run up
to 8.

```cmd
py main.py
```

### Which strands

| Switch | Effect |
|---|---|
| *(none)* | all strands |
| `--epica-only` | EPICA only |
| `--sisal-only` | SISAL only |
| `--ci-only` | the CI strand only |
| `--archaeo-only` | only the archaeological HTML pages |

The switches can be **combined**. `--ci-only --archaeo-only` runs the two
steps that belong together without touching EPICA and SISAL — the fastest
sensible run when working on the CI strand.

### Scope and format

| Switch | Default | Effect |
|---|---|---|
| `--sisal-sites dev` | `dev` | five sites, chosen so that every check of the generator still fires |
| `--sisal-sites all` | | all twelve sites of the cut |
| `--sisal-sites spannagel` | | one or more sites, by name or `site_id`, comma-separated |
| `--bundle-format nt` | `nt` | bundle as N-Triples only, fast |
| `--bundle-format release` | | N-Triples, Turtle, JSON-LD and RDF/XML |
| `--no-bundle` | | skip the bundle step altogether |
| `--no-overview` | | skip the overview map |
| `--no-visuals` | | skip the step for the documentation pages and slide figures. It runs only if `visuals/requirements.txt` is installed anyway |
| `--visuals-only` | | build only `docu/`, without the pipeline |
| `--no-clean` | | skip step 0 and write into the existing outputs |
| `--clean` | on | run step 0. This is the default anyway; the switch remains so that older invocations keep working |

A **release run** is everything that `--bundle-format release` sets. It brings
three things with it: `--sisal-sites all`, Turtle instead of N-Triples for the
large SISAL graphs, and print resolution for all raster graphics. Each of them
is reported when it overrides a default.

### Resolution of the raster graphics

| Switch | Effect |
|---|---|
| *(none)* | `draft` — 100 dpi, no pixel floor, small files |
| `--dpi print` | 300 dpi **and** at least 3,000 px on the shorter side |
| `--dpi 150` | exactly 150 dpi. From 300 the pixel floor applies, below it it does not |

The calculation is made on the finished, cropped image, not on the figure size —
which is why the output rarely says a round 300 dpi. For wide figures the
pixel floor wins: the SISAL world map ends up at 495 dpi.

The SVG next to every JPG has no resolution and is unaffected by all of this.

The value reaches the drawing scripts through the environment variable
`GEO_LOD_RASTER_DPI`, because each of them is a process of its own. Whoever
starts a script individually sets it themselves:

```cmd
set GEO_LOD_RASTER_DPI=print & py SISAL\plot_sisal_maps.py
```

### What a full run writes

```
ontology/geo_lod_core.ttl          the canonical ontology
ontology/vocab/mis.ttl             MIS vocabulary
ontology/trs.ttl                   temporal reference systems
dist/mis_stages.csv                MIS stages as a table
dist/mis_assignments.csv           MIS assignments as a table
EPICA/rdf/                         epica_dome_c.ttl, epica_ontology.ttl
EPICA/plots/                       78 figures of the five proxy records
EPICA/maps/                        epica_dome_c_map
EPICA/captions.yaml                one caption per figure
SISAL/rdf/                         sisal_sites.ttl, sisal_site_annotations.ttl,
                                   sisal_ontology.ttl, sisal_v3_core,
                                   sisal_v3_chronologies, sisal_v3_dating.ttl
SISAL/plots/                       profiles per speleothem and the cluster plates
SISAL/maps/                        world map and three cluster maps
SISAL/captions.yaml                73 entries
CI/rdf/                            ci_findspots.ttl, ci_site_annotations.ttl
CI/maps/                           three maps
CI/captions.yaml                   three entries
archaeo-connect/CI_findspots_CAA.html
maps/geo_lod_sites_map             the overview map, read from the graph
maps/captions.yaml
dist/geo-lod-bundle.*              the validated bundle
pipeline_report.txt                the log of the run
```

Run times for orientation, measured on a full run with twelve sites:
about 15 minutes, two thirds of it in the bundle step with the SHACL
validation. A `--ci-only --archaeo-only --no-bundle` run is through in a few
seconds.

---

## The individual scripts

All of them also run on their own, with `PYTHONPATH` pointing to `ontology`.
`main.py` sets that itself; by hand it goes like this:

```cmd
set PYTHONPATH=C:\git\GeoScience-FAIRification-LOD\ontology & py CI\ci_pipeline.py
```

### EPICA

| Script | Switches | Result |
|---|---|---|
| `EPICA/epica_rdf.py` | none | `EPICA/rdf/epica_dome_c.ttl`, `epica_ontology.ttl` |
| `EPICA/plot_epica_from_tab.py` | none | 78 figures to `EPICA/plots/` |
| `EPICA/epica_plates.py` | none | the plates, same directories |
| `EPICA/plot_epica_map.py` | none | `EPICA/maps/epica_dome_c_map` |

### SISAL

| Script | Switches | Result |
|---|---|---|
| `SISAL/sisal_import.py` | `--from PATH`, `--verify` | fetches the cut from `squirrels-sisal-db-v3` into `data/derived/sisal/`; `--verify` only checks against the manifest |
| `SISAL/sisal_rdf.py` | `--format nt\|turtle`, `--sites all\|dev\|NAME` | the six files in `SISAL/rdf/` |
| `SISAL/plot_sisal_from_csv.py` | none | profiles per speleothem to `SISAL/plots/` |
| `SISAL/plot_sisal_maps.py` | none | four maps to `SISAL/maps/` |

`--sites` takes `all`, `dev` (five sites) or a comma-separated list of names
and `site_id`s. Names are searched by prefix and regardless of upper and lower
case: `--sites spannagel` finds "Spannagel cave".

### CI and archaeology

| Script | Switches | Result |
|---|---|---|
| `CI/ci_pipeline.py` | none | `CI/rdf/ci_findspots.ttl`, `ci_site_annotations.ttl` |
| `CI/plot_ci_findspots.py` | none | three maps to `CI/maps/` |
| `archaeo-connect/ci_findspots_html.py` | none | `archaeo-connect/CI_findspots_CAA.html` |

### Across strands

| Script | Switches | Result |
|---|---|---|
| `plot_overview_map.py` | none | `maps/geo_lod_sites_map`, read from the TTL |
| `ontology/build_mis_vocab.py` | none | `ontology/vocab/mis.ttl`, `trs.ttl`, the two CSVs in `dist/` |
| `ontology/geo_lod_utils.py` | none | self-test of the shared building blocks |

`plot_overview_map.py` reads the freshly written Turtle files, not the input
tables. A strand whose TTL is missing is reported and named in the caption; a
planned strand such as ELSA stays silent until it exists.

---

## `bundle_rdf.py` — bundle and validation

```cmd
py bundle_rdf.py
```

| Switch | Effect |
|---|---|
| `--format nt,turtle,jsonld,xml` | output formats, comma-separated |
| `--sites spannagel` | a site bundle instead of the overall bundle |

Available formats: `nt`, `turtle`, `longturtle`, `xml`, `jsonld`.
The default is `nt` — writing the bundle of more than a million triples as
Turtle takes many times as long, and nobody reads it with their eyes in a
development run.

A site bundle requires a graph that contains the site:

```cmd
py main.py --sisal-only --sisal-sites spannagel --no-bundle & py bundle_rdf.py --sites spannagel --format turtle
```

Afterwards `dist/spannagel-bundle.ttl` exists — the file that `wdttest-sisal`
expects. It is in `.gitignore`.

---

## `check_docs.py` — does this file stay up to date?

```cmd
py check_docs.py
```

Collects all scripts with `__main__`, pulls out their `add_argument` switches
and holds both against `README-RUN.md`. Three things are reported: a script
that is missing here; a switch that is missing here; and a switch that is
listed here but that no script accepts any more.

`main.py` calls it in the preparation step. It is always a **warning** — a
documentation check that aborts a run is one that gets switched off.

| Switch | Effect |
|---|---|
| `--verbose` | list every entry point with its switches |

The prose remains manual work. What a script *writes* is unknown to any parser,
and that is the more useful half of this file — the check covers the other.

---

## `clean.py` — what is generated, what is left over

Without a switch **nothing** is deleted, it is only listed:

```cmd
py clean.py
```

Three headings, and the difference matters:

- **Generated** — written afresh on every run by the step that owns the file
- **Unused leftovers** — written once, read by nothing any more
- **Scheduled** — in use, but with an expiry date. Is **never** removed here,
  whatever the switch. The message at the end of a run is a reminder, not a
  request.

| Switch | Effect |
|---|---|
| `--delete` | really remove the generated files |
| `--delete --stale` | additionally the leftovers |
| `--group NAME` | restrict to one group, repeatable |
| `--list-groups` | show the groups and exit |

Groups: `vocab`, `diagrams`, `epica`, `sisal`, `overview`, `ci`, `archaeo`,
`bundle`, `cache` and `log`, where `log` is not in the default set.

`main.py` calls `clean.py` in step 0 with exactly the groups that the run
rewrites afterwards — which is why the outputs of EPICA and SISAL stay
untouched after a `--ci-only` run.

---

## Checks that are worth it

**Byte stability.** Two runs on unchanged inputs must produce the same bytes.
The only permitted exception is `pipeline_report.txt`.

```cmd
py main.py --ci-only --archaeo-only --no-bundle & git add -A & py main.py --ci-only --archaeo-only --no-bundle & git status --short
```

It is clean if only `pipeline_report.txt` carries an `M` in the **second**
column. Both runs must use the same resolution, otherwise the JPGs naturally
change, and that would not be a finding.

**The cut against its manifest.**

```cmd
py SISAL\sisal_import.py --verify
```

**Completeness before a release.**

```cmd
py main.py --bundle-format release
```

Expected: CRM coverage without a gap, zero SHACL violations. A warning about
`cisite_59` is known and open — Kostenki-Borshchevo does not yet carry a
`skos:closeMatch` to an external authority file.

---

## When something does not run

| Message | Cause |
|---|---|
| `ModuleNotFoundError: geo_lod_utils` | `PYTHONPATH` does not point to `ontology/`. `main.py` sets that itself |
| `data/raw/basemap/ne_50m_land.geojson not found` | the base map is missing; it is 1.6 MB and does not travel with every bundle |
| `none of SISAL/rdf/sisal_sites.ttl … found` | the overview map ran before the SISAL step |
| `columns missing from cifindspots_part_full.csv` | the findspot table comes from a different version of `campanian-ignimbrite-geo` |
| The bundle step takes forever | that is the SHACL validation over more than a million triples. `--no-bundle` skips it |

## `visuals/build.py` — documentation and figures

```cmd
py -m pip install -r visuals\requirements.txt && py visuals\build.py
```

Builds both: twelve slide figures as SVG and PNG plus `slides.html` and the cluster pages, and the documentation, all into `docu/` (`index`, `model`, `crm-coverage`, `crosswalk`, `instances`, `sparql` with figures, `downloads/queries/*.rq` and the sample graph `data/geo-lod-sample.nt`). `--only slides` or `--only docu` builds one half. Within a `main.py` run it is the step after the bundle; `py main.py --visuals-only` runs only it. `visuals/docu.py` and `visuals/sample_graph.py` are the parts from which `docu/` arises. The workflow `docu-pages.yml` publishes `docu/` under `/docu/` on GitHub Pages and places a redirect page (`pages-root/index.html`) on the root; the Unicorn pages (`main.yml`) live under `/semweb/`.
