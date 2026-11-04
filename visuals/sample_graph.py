"""The graph behind the query page: every ontology file, the full CI and SISAL site layers and a regular cut of the dense series.

The page parses the graph in the browser under Pyodide, so it has to stay small. EPICA holds about 190 000 triples and the
SISAL dating layer 25 000; the page gets every 50th EPICA observation with its time position, MIS membership and sample, and
every 6th SISAL dating point. All resources that are not one of those per-observation records (sites, cores, data sources,
smoothing methods, MIS boundaries, units) are kept whole. The cut is by the number in the identifier, so it does not change
when the data are regenerated in the same order.

Written as sorted N-Triples with blank nodes relabelled by their content hash, so a second run writes the same bytes.
"""
from __future__ import annotations

import re
from hashlib import sha1
from pathlib import Path

from rdflib import BNode, Graph, URIRef

REPO = Path(__file__).resolve().parent.parent
ONTOLOGY = ["ontology/geo_lod_core.ttl", "ontology/strat.ttl", "ontology/analysis_core.ttl", "ontology/crm_bridging.ttl",
            "ontology/trs.ttl", "EPICA/rdf/epica_ontology.ttl", "SISAL/rdf/sisal_ontology.ttl"]
FULL = ["CI/rdf/ci_findspots.ttl", "CI/rdf/ci_site_annotations.ttl", "SISAL/rdf/sisal_sites.ttl",
        "SISAL/rdf/sisal_site_annotations.ttl"]
EPICA_EVERY, SISAL_EVERY = 50, 6
_EPICA_REC = re.compile(r"/epica/(?:obs|tp|mis_membership|sample)_.*?_?(\d+)(?:_edc\d_gas)?$")
_DATING = re.compile(r"/sisal/datingpoint_(\d+)$")


def _keep(s: str) -> bool:
    m = _EPICA_REC.search(s)
    if m:
        return int(m.group(1)) % EPICA_EVERY == 0
    m = _DATING.search(s)
    if m:
        return int(m.group(1)) % SISAL_EVERY == 0
    return True


def build(repo: Path = REPO) -> Graph:
    g = Graph()
    for f in ONTOLOGY + FULL:
        g.parse(repo / f, format="turtle")
    for f in ("EPICA/rdf/epica_dome_c.ttl", "SISAL/rdf/sisal_v3_dating.ttl"):
        for s, p, o in Graph().parse(repo / f, format="turtle"):
            if isinstance(s, URIRef) and not _keep(str(s)):
                continue
            if isinstance(o, URIRef) and not _keep(str(o)):
                continue
            g.add((s, p, o))
    return g


def _label_bnodes(g: Graph) -> Graph:
    """Blank nodes get an id from what they say, so the file does not depend on parser order."""
    out = Graph()
    def desc(b, seen=()):
        parts = sorted(f"{p}|{o if not isinstance(o, BNode) else '_'}" for p, o in g.predicate_objects(b))
        parts += sorted(f"^{p}|{s if not isinstance(s, BNode) else '_'}" for s, p in g.subject_predicates(b))
        return sha1("\n".join(parts).encode()).hexdigest()[:16]
    ids = {}
    for b in {x for t in g for x in t if isinstance(x, BNode)}:
        ids[b] = BNode("b" + desc(b))
    if len(set(ids.values())) != len(ids):
        raise SystemExit("sample graph: two blank nodes with identical descriptions")
    for s, p, o in g:
        out.add((ids.get(s, s), p, ids.get(o, o)))
    return out


def write(dest: Path, repo: Path = REPO) -> int:
    g = _label_bnodes(build(repo))
    lines = sorted(t.rstrip() for t in g.serialize(format="nt").splitlines() if t.strip())
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(lines)


if __name__ == "__main__":
    n = write(Path("/tmp/t1/sample.nt"))
    print(n, Path("/tmp/t1/sample.nt").stat().st_size)
