"""The geo-lod data model, read from the ontology files.

Everything the model pages and model figures say about classes, properties, domains, ranges and CRM anchors is read here,
from the same files the pipeline publishes. Nothing is typed in by hand except `STATED`, the counts that figures 08 and
12 print; `check()` stops the build when the ontology no longer agrees with them.

Modules (one file each):

    core    ontology/geo_lod_core.ttl          geolod:
    epica   EPICA/rdf/epica_ontology.ttl       geolod: (extension)
    sisal   SISAL/rdf/sisal_ontology.ttl       geolod: (extension)
    strat   ontology/strat.ttl                 strat:
    an      ontology/analysis_core.ttl         an:

`ontology/crm_bridging.ttl` is read with them: its axioms are what carries SOSA, PROV, SKOS, GeoSPARQL and OWL-Time
classes into the CIDOC CRM family, and a class counts as anchored when a chain of rdfs:subClassOf axioms from any of
these files reaches a class in a CRM-family namespace (the rule of ontology/README.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

REPO = Path(__file__).resolve().parent.parent
MODULES = {
    "core": ("geo-lod core", "ontology/geo_lod_core.ttl"),
    "epica": ("EPICA extension", "EPICA/rdf/epica_ontology.ttl"),
    "sisal": ("SISAL extension", "SISAL/rdf/sisal_ontology.ttl"),
    "strat": ("strat", "ontology/strat.ttl"),
    "an": ("an", "ontology/analysis_core.ttl"),
}
ORDER = list(MODULES)
BRIDGING = "ontology/crm_bridging.ttl"
# Files that carry no class or property of their own but whose namespaces and instances the query page uses.
EXTRA_ONTOLOGY_FILES = ["ontology/trs.ttl"]

# CRM-family namespaces, with the short name used on the pages. The CRMarchaeo namespace is written both ways in the
# project's own documents; both count.
FAMILIES = {
    "http://www.cidoc-crm.org/cidoc-crm/": ("crm", "CIDOC CRM"),
    "http://www.ics.forth.gr/isl/CRMsci/": ("sci", "CRMsci"),
    "http://www.ics.forth.gr/isl/CRMgeo/": ("geo", "CRMgeo"),
    "http://www.cidoc-crm.org/extensions/crmarchaeo/": ("arch", "CRMarchaeo"),
    "http://www.ics.forth.gr/isl/CRMarchaeo/": ("arch", "CRMarchaeo"),
}
OWN = {"strat": "http://w3id.org/geo-lod/strat/", "an": "http://w3id.org/geo-lod/analysis/",
       "geolod": "http://w3id.org/geo-lod/"}

# What figures 08 and 12 print about the model. check() compares these with the ontology.
STATED = {"geolod": 46, "strat": 10, "an": 6}


def ns_key(iri: str) -> str | None:
    """geolod, strat or an for a term of our own namespaces, else None. A term has no further '/' in its local part."""
    for key in ("strat", "an", "geolod"):
        ns = OWN[key]
        if iri.startswith(ns) and "/" not in iri[len(ns):] and "#" not in iri[len(ns):]:
            return key
    return None


def family(iri: str) -> str | None:
    for ns, (short, _) in FAMILIES.items():
        if iri.startswith(ns):
            return short
    return None


@dataclass
class Cls:
    iri: str
    curie: str
    label: str
    comment: str
    modules: list[str]
    ns: str                                # geolod / strat / an

    @property
    def primary(self) -> str:
        return self.modules[0]

    @property
    def local(self) -> str:
        return self.curie.split(":", 1)[1]


@dataclass
class Prop:
    iri: str
    curie: str
    kind: str                              # object / datatype
    label: str
    comment: str
    modules: list[str]
    domains: list[str] = field(default_factory=list)      # IRIs
    ranges: list[str] = field(default_factory=list)

    @property
    def ns(self) -> str:
        return ns_key(self.iri)

    @property
    def local(self) -> str:
        return self.curie.split(":", 1)[1]


class Model:
    def __init__(self, repo: Path = REPO):
        self.repo = repo
        self.graphs = {k: Graph().parse(repo / f, format="turtle") for k, (_, f) in MODULES.items()}
        self.bridging = Graph().parse(repo / BRIDGING, format="turtle")
        self.merged = Graph()
        for g in [*self.graphs.values(), self.bridging]:
            for t in g:
                self.merged.add(t)
        self._prefixes: dict[str, str] = {}
        for g in [*self.graphs.values(), self.bridging]:
            for pfx, ns in g.namespaces():
                self._prefixes.setdefault(str(ns), pfx)
        self._prefixes.update({OWN["geolod"]: "geolod", OWN["strat"]: "strat", OWN["an"]: "an"})
        self._read()

    # ---- names
    def curie(self, iri: str) -> str:
        best = ""
        for ns in self._prefixes:
            if iri.startswith(ns) and len(ns) > len(best) and "/" not in iri[len(ns):] and "#" not in iri[len(ns):]:
                best = ns
        return f"{self._prefixes[best]}:{iri[len(best):]}" if best else iri

    def _lit(self, g: Graph, s, p) -> str:
        vals = sorted(str(o) for o in g.objects(s, p) if isinstance(o, Literal) and o.language in (None, "en"))
        return " ".join(vals[0].split()) if vals else ""

    # ---- classes and properties
    def _read(self) -> None:
        classes: dict[str, Cls] = {}
        props: dict[str, Prop] = {}
        for mod in ORDER:
            g = self.graphs[mod]
            for c in sorted(set(g.subjects(RDF.type, OWL.Class)), key=str):
                if isinstance(c, BNode) or not ns_key(str(c)):
                    continue
                iri = str(c)
                cur = classes.get(iri)
                if cur is None:
                    classes[iri] = Cls(iri, self.curie(iri), self._lit(g, c, RDFS.label), self._lit(g, c, RDFS.comment),
                                       [mod], ns_key(iri))
                else:
                    cur.modules.append(mod)
                    cur.label = cur.label or self._lit(g, c, RDFS.label)
                    cur.comment = cur.comment or self._lit(g, c, RDFS.comment)
            for kind, typ in (("object", OWL.ObjectProperty), ("datatype", OWL.DatatypeProperty)):
                for p in sorted(set(g.subjects(RDF.type, typ)), key=str):
                    if isinstance(p, BNode) or not ns_key(str(p)):
                        continue
                    iri = str(p)
                    cur = props.get(iri)
                    if cur is None:
                        cur = props[iri] = Prop(iri, self.curie(iri), kind, self._lit(g, p, RDFS.label),
                                                self._lit(g, p, RDFS.comment), [mod])
                    elif mod not in cur.modules:
                        cur.modules.append(mod)
                        cur.comment = cur.comment or self._lit(g, p, RDFS.comment)
                    for o in sorted(g.objects(p, RDFS.domain), key=str):
                        if isinstance(o, URIRef) and str(o) not in cur.domains:
                            cur.domains.append(str(o))
                    for o in sorted(g.objects(p, RDFS.range), key=str):
                        if isinstance(o, URIRef) and str(o) not in cur.ranges:
                            cur.ranges.append(str(o))
        self.classes = classes
        self.props = props

    def classes_of(self, *modules: str) -> list[Cls]:
        """Classes whose first declaring module is one of `modules`, sorted by name."""
        return sorted((c for c in self.classes.values() if c.primary in modules), key=lambda c: c.curie)

    def props_of(self, *modules: str) -> list[Prop]:
        return sorted((p for p in self.props.values() if p.modules[0] in modules), key=lambda p: (p.kind, p.curie))

    # ---- hierarchy and CRM anchors
    def parents(self, iri: str) -> list[str]:
        ps = {str(o) for o in self.merged.objects(URIRef(iri), RDFS.subClassOf) if isinstance(o, URIRef)}
        return sorted(ps, key=lambda p: (family(p) is None, self.curie(p)))

    def anchors(self, iri: str) -> tuple[list[str], list[str]]:
        """Nearest CRM-family ancestors and one chain to the first of them: ([anchor, ...], [iri, ..., anchor]).

        Breadth first over rdfs:subClassOf, so the nearest anchors are the ones found at the smallest depth.
        Empty lists when no chain reaches the CRM family."""
        seen = {iri: None}
        level = [iri]
        while level:
            found = sorted({n for n in level if family(n) and n != iri}, key=self.curie)
            if found:
                chain, node = [], found[0]
                while node is not None:
                    chain.append(node)
                    node = seen[node]
                return found, chain[::-1]
            nxt = []
            for n in level:
                for p in self.parents(n):
                    if p not in seen:
                        seen[p] = n
                        nxt.append(p)
            level = nxt
        return [], []

    def anchored(self) -> dict[str, tuple[list[str], list[str]]]:
        return {iri: self.anchors(iri) for iri in sorted(self.classes)}

    # ---- numbers and checks
    def counts(self) -> dict[str, dict[str, int]]:
        out = {}
        for key in ("geolod", "strat", "an"):
            cs = [c for c in self.classes.values() if c.ns == key]
            anchored = [c for c in cs if self.anchors(c.iri)[0]]
            out[key] = {"classes": len(cs), "anchored": len(anchored),
                        "object": sum(1 for p in self.props.values() if p.ns == key and p.kind == "object"),
                        "datatype": sum(1 for p in self.props.values() if p.ns == key and p.kind == "datatype")}
        return out

    def check(self) -> list[str]:
        """Messages for what no longer holds. A message is a stop, not a warning."""
        problems = []
        counts = self.counts()
        for key, n in STATED.items():
            if counts[key]["classes"] != n:
                problems.append(f"figures 08/12 state {n} classes for {key}:, the ontology files hold {counts[key]['classes']}")
        loose = [c.curie for c in self.classes.values() if c.ns == "geolod" and not self.anchors(c.iri)[0]]
        if loose:
            problems.append("geolod: classes without a CRM-family ancestor (the N4O rule): " + ", ".join(sorted(loose)))
        return problems

    def uncommented(self) -> list[Prop]:
        """Properties without an rdfs:comment: a gap in the documentation, reported on the model page."""
        return sorted((p for p in self.props.values() if not p.comment), key=lambda p: p.curie)
