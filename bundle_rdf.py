#!/usr/bin/env python3
"""
bundle_rdf.py - Aggregate ontology + instance RDF into a single distributable
                 Turtle file under dist/, then run validations.

Pipeline-Schritt 5:
  1. Merge alle TTL-Dateien aus ontology/, EPICA/rdf/, SISAL/rdf/, CI/rdf/
     into an rdflib.Graph -> dist/geo-lod-bundle.ttl
     (with defensive auto-repair for multi-line string literals)
  2. CIDOC-CRM coverage: every typed instance must hang (transitively via
     rdfs:subClassOf) under a CRM-family class
     (crm:, crmsci:, crmarchaeo:, crmgeo:)
  3. SHACL-Validierung gegen ontology/shapes/*.ttl bzw. ontology/*-shapes.ttl
  4. Sanity-Checks (Triple-Count, Klassen-/Property-Inventar)

Direct call:       python bundle_rdf.py
Call through main: calls run_bundle_step(...).
"""

from __future__ import annotations

import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

try:
    from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef
except ImportError as e:
    print(f"  ✗ rdflib not available: {e}")
    print("    Install with:  pip install rdflib")
    raise

# pyshacl is optional - SHACL validation is skipped if it is not available.
try:
    from pyshacl import validate as shacl_validate

    PYSHACL_AVAILABLE = True
except ImportError:
    PYSHACL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Namespaces - CIDOC-CRM-Familie
# ---------------------------------------------------------------------------
# Strict CRM coverage: ALL classes, including external standard vocabularies
# (SOSA, PROV, GeoSPARQL, DCAT, FOAF, ...), must receive a CRM anchor,
# because the bundle flows into the NFDI4Objects Knowledge Graph.
# For external vocabularies this happens by a bridging axiom in the project's
# own ontology (see ontology/README.md - crosswalk).

CRM_FAMILY_PREFIXES = (
    "http://www.cidoc-crm.org/cidoc-crm/",
    "http://www.ics.forth.gr/isl/CRMsci/",
    "http://www.ics.forth.gr/isl/CRMgeo/",
    "http://www.ics.forth.gr/isl/CRMarchaeo/",
    "http://www.cidoc-crm.org/extensions/crmsci/",
    "http://www.cidoc-crm.org/extensions/crmgeo/",
    "http://www.cidoc-crm.org/extensions/crmarchaeo/",
)

GEO_LOD = Namespace("http://w3id.org/geo-lod/")


# ---------------------------------------------------------------------------
# TTL Auto-Repair
# ---------------------------------------------------------------------------
# Known problem in the generator scripts: multi-line string literals
# are written with normal "..." quotes, which Turtle does not allow.
# We repair this in memory on re-parse - but the source still has to
# be fixed. See the notes in the output and ontology/README.md.

# Matches: a plain "..." literal that contains at least one newline.
_BROKEN_LITERAL = re.compile(
    r'"((?:[^"\\]|\\.)*?\n(?:[^"\\]|\\.)*?)"',
    re.DOTALL,
)


def _repair_multiline_strings(ttl_text: str) -> tuple[str, int]:
    """Replace plain "..." literals that contain newlines with
    triple-quoted literals.

    Returns (repaired text, number of replacements). Conservative: replaces
    only if the string does not itself contain \"\"\" already.
    """
    n = 0

    def _repl(m: re.Match) -> str:
        nonlocal n
        content = m.group(1)
        if '"""' in content:
            return m.group(0)  # nicht anfassen
        n += 1
        return f'"""{content}"""'

    return _BROKEN_LITERAL.sub(_repl, ttl_text), n


def _parse_with_repair(graph: Graph, path: Path) -> tuple[int, int, bool]:
    """Try normal parsing first, fall back to auto-repair on error.

    Returns: (added_triples, file_triples, repaired_flag)
      - added_triples: how many triples are NEW in the graph from this parse
      - file_triples:  how many triples the file itself contains (for display
                       of aggregates whose content is already in the bundle)
      - repaired_flag: True if auto-repair had to step in

    Raises an exception only if the repair attempt fails as well.
    """
    before = len(graph)
    repaired_flag = False

    try:
        graph.parse(path, format="turtle")
    except Exception as first_err:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig")

        repaired, n_fixes = _repair_multiline_strings(text)
        if n_fixes == 0:
            raise first_err

        graph.parse(data=repaired, format="turtle")
        repaired_flag = True

    added = len(graph) - before

    # Parse the file in isolation to learn its intrinsic triple count.
    # This is only necessary if 'added' does not correspond to the full file
    # (that is: set duplicates with material already loaded).
    # We always count, because it is cheap.
    file_graph = Graph()
    try:
        file_graph.parse(path, format="turtle")
    except Exception:
        if repaired_flag:
            file_graph.parse(data=repaired, format="turtle")
        else:
            # Should not happen - if the first parse worked, this one will too
            pass
    file_triples = len(file_graph)

    return added, file_triples, repaired_flag


# ---------------------------------------------------------------------------
# Bundle Builder
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------
#
# Measured on a bundle of about 208,000 triples (10 MB Turtle):
#
#   nt          1.4s   30.1 MB   fast, line by line, easy to grep
#   xml         2.7s   21.3 MB
#   turtle      6.6s   10.4 MB   compact and readable - the release format
#   longturtle  6.4s   10.6 MB
#   json-ld     8.9s   28.7 MB
#
# The default is Turtle. N-Triples would be faster, but measurably saves only
# about 13 of the 187 seconds of a full run - too little to justify accepting
# that the versioned .ttl lags behind the code and that one has to remember a
# flag. Whoever iterates tightly uses --bundle-format nt; for a
# publication, --bundle-format release writes all formats.

BUNDLE_FORMATS: dict[str, tuple[str, str, str]] = {
    # Key: (rdflib format, file extension, description)
    # Note: N-Triples is not byte-stable. rdflib assigns new blank-node labels
    # on parsing, and N-Triples writes them out in plain text -
    # about 30 lines with OWL restrictions therefore change on every run.
    # That is why dist/geo-lod-bundle.nt is in .gitignore. Turtle stays
    # stable because the same nodes are serialised inline as [ ] there.
    "nt": ("nt", ".nt", "N-Triples - one line per triple, fastest"),
    "turtle": ("turtle", ".ttl", "Turtle - compact and readable, release format"),
    "longturtle": ("longturtle", ".lttl", "Turtle with one predicate per line"),
    "xml": ("xml", ".rdf", "RDF/XML - for tools that read nothing else"),
    "jsonld": ("json-ld", ".jsonld", "JSON-LD - for web clients"),
}

# N-Triples for a development run: writing the 1.2-million-triple bundle as
# Turtle took 373s against roughly 60s here, and nothing in a development run
# reads the bundle with its eyes. Turtle is still written by a release run,
# where RELEASE_BUNDLE_FORMATS asks for all four.
DEFAULT_BUNDLE_FORMATS: tuple[str, ...] = ("nt",)
RELEASE_BUNDLE_FORMATS: tuple[str, ...] = ("nt", "turtle", "jsonld", "xml")

# Aggregate files: unions of files that are loaded individually anyway.
# They add nothing to the bundle but cost a full parse.
# Checked 2026-08-08: without sisal_all_data.ttl the bundle keeps an
# identical triple count and the step becomes about a third faster.
AGGREGATE_FILENAMES: set[str] = {"sisal_all_data.ttl"}

# Files a development run leaves out. sisal_v3_chronologies.ttl holds the
# 101 470 competing ages from the seven models geo-lod does not follow: 885 000
# triples that no figure and no shape needs, and roughly half the parse time of
# the whole bundle. They belong in a release, not in every run.
#
# Nothing is lost by leaving them out. The age geo-lod follows is materialised
# on the sample in sisal_v3_core.ttl, and the file stands on its own next to
# the bundle for anyone comparing models.
# Matched on the stem, because the same graph is written as .nt in a
# development run and as .ttl in a release one.
RELEASE_ONLY_STEMS: set[str] = {"sisal_v3_chronologies"}

# Instance graphs may arrive in either format. Turtle first so that a stale
# .ttl next to a fresh .nt is still found and reported rather than silently
# ignored; _dedupe_formats then keeps one per stem.
INSTANCE_SUFFIXES: tuple[str, ...] = (".ttl", ".nt")


def _dedupe_formats(paths: list[Path]) -> list[Path]:
    """One file per stem, preferring the format written most recently.

    A release run writes sisal_v3_core.ttl next to the sisal_v3_core.nt a
    development run left behind. Reading both would load every triple twice,
    which rdflib survives and the triple count does not - and a stale one
    would quietly outvote the fresh one.
    """
    by_stem: dict[str, Path] = {}
    for path in paths:
        current = by_stem.get(path.stem)
        if current is None or path.stat().st_mtime > current.stat().st_mtime:
            by_stem[path.stem] = path
    return [by_stem[stem] for stem in sorted(by_stem)]


def _collect_ttl_files(source_dirs: Iterable[Path],
                       release: bool = False,
                       suffixes: tuple[str, ...] = (".ttl",)) -> list[Path]:
    files: list[Path] = []
    skipped: list[Path] = []
    for d in source_dirs:
        if not d.exists():
            continue
        found: list[Path] = []
        for suffix in suffixes:
            found.extend(sorted(d.glob(f"*{suffix}")))
        for path in _dedupe_formats(found):
            if not release and path.stem in RELEASE_ONLY_STEMS:
                skipped.append(path)
                continue
            files.append(path)
    for path in skipped:
        print(f"  ℹ  {path.name} skipped - only in the release bundle. "
              f"With --bundle-format release it is included.")
    return files


def _dedupe_core_copies(files: list[Path], canonical_ontology_dir: Path) -> list[Path]:
    """If sub-scripts write a copy of e.g. geo_lod_core.ttl into their rdf/
    directories, we ignore it - the canonical version
    lives in ontology/.
    """
    canonical_names = {p.name for p in canonical_ontology_dir.glob("*.ttl")}

    kept: list[Path] = []
    skipped: list[Path] = []
    for f in files:
        if f.parent == canonical_ontology_dir:
            kept.append(f)
            continue
        if f.name in canonical_names:
            skipped.append(f)
            continue
        kept.append(f)

    if skipped:
        print("    (Duplicates ignored - canonical version lives in ontology/):")
        for f in skipped:
            print(f"      ~ {f}")
    return kept


def build_bundle(
    ontology_dir: Path,
    rdf_dirs: Iterable[Path],
    output_path: Path,
    formats: Iterable[str] = DEFAULT_BUNDLE_FORMATS,
) -> Graph | None:
    """Merge all TTLs into one graph and write to output_path."""
    print("\n  ▶ Collecting TTL sources ...")

    # ontology/*.ttl plus the controlled vocabularies in ontology/vocab/.
    # ontology/shapes/ stays out - shapes do not belong in the data graph.
    # "Release" is read off the formats rather than passed as a second switch:
    # a run that asks for the release formats is the release run, and two
    # independent flags would eventually disagree.
    release = set(formats) >= set(RELEASE_BUNDLE_FORMATS)
    ontology_files = _collect_ttl_files([ontology_dir, ontology_dir / "vocab"])
    instance_files = _collect_ttl_files(rdf_dirs, release=release,
                                        suffixes=INSTANCE_SUFFIXES)

    print(f"    Ontology files: {len(ontology_files)}")
    for f in ontology_files:
        try:
            print(f"      • {f.relative_to(ontology_dir.parent)}")
        except ValueError:
            print(f"      • {f}")

    instance_files = _dedupe_core_copies(instance_files, ontology_dir)

    aggregates = [f for f in instance_files if f.name in AGGREGATE_FILENAMES]
    if aggregates:
        print("    (Aggregates skipped - content is already in the individual files):")
        for f in aggregates:
            print(f"      ~ {f.name}")
        instance_files = [f for f in instance_files if f.name not in AGGREGATE_FILENAMES]

    print(f"    Instance files: {len(instance_files)}")
    for f in instance_files:
        try:
            print(f"      • {f.relative_to(ontology_dir.parent)}")
        except ValueError:
            print(f"      • {f}")

    all_files = ontology_files + instance_files
    if not all_files:
        print("  ✗ No TTL files found - bundle not created.")
        return None

    g = Graph()
    g.bind("crm", Namespace(CRM_FAMILY_PREFIXES[0]))
    g.bind("crmsci", Namespace("http://www.ics.forth.gr/isl/CRMsci/"))
    g.bind("crmgeo", Namespace("http://www.ics.forth.gr/isl/CRMgeo/"))
    g.bind("crmarchaeo", Namespace("http://www.ics.forth.gr/isl/CRMarchaeo/"))
    g.bind("geo-lod", GEO_LOD)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)

    print("\n  ▶ Parse & merge ...")
    parse_errors: list[tuple[Path, str]] = []
    repaired_files: list[Path] = []

    for f in all_files:
        try:
            added, file_triples, was_repaired = _parse_with_repair(g, f)
            tag = "  (auto-repaired)" if was_repaired else ""
            # If all triples are new: show only one number.
            # If the file contains more triples than it contributes to the bundle
            # (= aggregate / set duplicates), show both numbers.
            if added == file_triples:
                print(f"    + {f.name}: {file_triples:>8,} Triples{tag}")
            else:
                print(
                    f"    + {f.name}: {file_triples:>8,} Triples "
                    f"({added:,} new, {file_triples - added:,} dup){tag}"
                )
            if was_repaired:
                repaired_files.append(f)
        except Exception as e:
            short = str(e).splitlines()[0][:120]
            print(f"    ✗ Error parsing {f.name}: {short}")
            parse_errors.append((f, str(e)))

    if repaired_files:
        print()
        print("  ⚠  Auto-repair applied - FIX NEEDED IN GENERATOR SCRIPTS:")
        for f in repaired_files:
            print(f"      • {f}")
        print('    → Multi-line string literals must be written with """..."""')
        print('      instead of "..." (Turtle spec).')

    if parse_errors:
        print(f"\n  ⚠  {len(parse_errors)} file(s) could not be parsed.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n  ▶ Serialising bundle ({len(g):,} triples) ...")

    written: set[str] = set()

    for key in formats:
        if key not in BUNDLE_FORMATS:
            print(f"    ⚠  Unknown format skipped: {key}")
            continue
        rdflib_format, suffix, description = BUNDLE_FORMATS[key]
        target = output_path.with_suffix(suffix)
        t_start = time.perf_counter()
        g.serialize(destination=target, format=rdflib_format, encoding="utf-8")
        size_mb = target.stat().st_size / 1048576
        print(
            f"  ✓ {target.name:<26} {size_mb:6.1f} MB  "
            f"{time.perf_counter() - t_start:5.1f}s  ({description})"
        )
        written.add(target.name)

    # Bundles from earlier runs that were not rewritten this time
    # are now stale. Quietly leaving them in place would be the more dangerous
    # option: they look current and are not.
    stale = sorted(
        f.name
        for f in output_path.parent.glob(output_path.stem + ".*")
        if f.name not in written
    )
    if stale:
        print("\n  ℹ  From earlier runs, not rewritten in this run:")
        for name in stale:
            print(f"      • {name}")
        print("     Before a publication: python main.py --bundle-format release")

    return g


# ---------------------------------------------------------------------------
# Validation: CIDOC-CRM Coverage (strict)
# ---------------------------------------------------------------------------


def _is_crm_class(uri: URIRef) -> bool:
    s = str(uri)
    return any(s.startswith(p) for p in CRM_FAMILY_PREFIXES)


def validate_crm_coverage(g: Graph) -> bool:
    """Strict: every typed instance must hang, via the rdfs:subClassOf closure,
    under a class from the CIDOC CRM family
    (crm: / crmsci: / crmgeo: / crmarchaeo:).

    External vocabularies (SOSA, PROV, GeoSPARQL, DCAT, FOAF, ...) are NOT
    counted as 'ok' - they need a bridging axiom in the project's own
    ontology. See ontology/README.md (crosswalk).
    """

    instance_classes: set[URIRef] = {
        o for _, _, o in g.triples((None, RDF.type, None)) if isinstance(o, URIRef)
    }

    skip = {
        OWL.Class,
        OWL.NamedIndividual,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.Ontology,
        OWL.AnnotationProperty,
        OWL.Restriction,
        OWL.AllDisjointClasses,
        OWL.AllDifferent,
        RDFS.Class,
        RDFS.Datatype,
        RDF.Property,
        RDF.List,
        # Property characteristics. They appear as a second rdf:type next to
        # owl:ObjectProperty and state how a property behaves -
        # not an entity that could have a CRM ancestor. Noticed with
        # S3c.3: strat.ttl declares the Allen relations on the depth axis
        # as transitive or symmetric, and the check read this as
        # five instances of two unanchored classes.
        OWL.TransitiveProperty,
        OWL.SymmetricProperty,
        OWL.AsymmetricProperty,
        OWL.ReflexiveProperty,
        OWL.IrreflexiveProperty,
        OWL.FunctionalProperty,
        OWL.InverseFunctionalProperty,
        OWL.DeprecatedClass,
        OWL.DeprecatedProperty,
    }
    instance_classes -= skip

    if not instance_classes:
        print("    ⚠  No typed instances found - check skipped.")
        return True

    def ancestors(cls: URIRef, seen: set[URIRef] | None = None) -> set[URIRef]:
        if seen is None:
            seen = set()
        for parent in g.objects(cls, RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in seen:
                seen.add(parent)
                ancestors(parent, seen)
        return seen

    covered: list[URIRef] = []
    uncovered: list[URIRef] = []
    for cls in sorted(instance_classes):
        chain = {cls} | ancestors(cls)
        if any(_is_crm_class(c) for c in chain):
            covered.append(cls)
        else:
            uncovered.append(cls)

    print(f"    Instance classes checked: {len(instance_classes)}")
    print(f"    ✓ with CRM anchor:        {len(covered)}")
    print(f"    ✗ without CRM anchor:     {len(uncovered)}")

    if uncovered:
        print("\n    Classes without CRM anchor (crosswalk in ontology/README.md):")
        with_counts = sorted(
            ((cls, sum(1 for _ in g.subjects(RDF.type, cls))) for cls in uncovered),
            key=lambda x: (-x[1], str(x[0])),
        )
        for cls, n_inst in with_counts:
            print(f"      • {cls}  ({n_inst} instance(s))")
        return False

    return True


# ---------------------------------------------------------------------------
# Validation: SHACL
# ---------------------------------------------------------------------------


def _find_shape_files(ontology_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    shapes_dir = ontology_dir / "shapes"
    if shapes_dir.exists():
        candidates.extend(sorted(shapes_dir.glob("*.ttl")))
    candidates.extend(sorted(ontology_dir.glob("*-shapes.ttl")))
    candidates.extend(sorted(ontology_dir.glob("*_shapes.ttl")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def validate_shacl(g: Graph, ontology_dir: Path) -> bool:
    print("\n  ▶ SHACL validation ...")

    if not PYSHACL_AVAILABLE:
        print("    ⚠  pyshacl not installed - skipped.")
        print("       Installation:  pip install pyshacl")
        return True

    shape_files = _find_shape_files(ontology_dir)
    if not shape_files:
        print("    ⚠  No shape files found - skipped.")
        print(f"       Expected e.g. under: {ontology_dir / 'shapes'}/*.ttl")
        return True

    shapes_graph = Graph()
    for sf in shape_files:
        print(f"    + lade Shapes: {sf.name}")
        shapes_graph.parse(sf, format="turtle")

    # inference="none", not "rdfs": the RDFS reasoner over 200k triples
    # cost two thirds of the run time of the step (42 s versus 14 s)
    # and changes nothing in the result. SHACL follows rdfs:subClassOf for
    # sh:targetClass and sh:class by itself; the subclass axioms only
    # have to be in the bundle for that, and they are (geo_lod_core.ttl,
    # crm_bridging.ttl). Checked 2026-08-08: identical results.
    t_start = time.perf_counter()
    conforms, results_graph, results_text = shacl_validate(
        data_graph=g,
        shacl_graph=shapes_graph,
        ont_graph=None,
        inference="none",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        debug=False,
    )
    print(f"    Dauer: {time.perf_counter() - t_start:.1f}s")

    if conforms:
        print("    ✓ All SHACL shapes satisfied.")
        return True

    # Conforms=False can be triggered by violations OR warnings.
    # Only sh:Violation should block the bundle - warnings are audit notes.
    SH = Namespace("http://www.w3.org/ns/shacl#")
    n_violations = 0
    n_warnings = 0
    n_other = 0
    for r in results_graph.subjects(RDF.type, SH.ValidationResult):
        sev = next(results_graph.objects(r, SH.resultSeverity), None)
        if sev == SH.Violation:
            n_violations += 1
        elif sev == SH.Warning:
            n_warnings += 1
        else:
            n_other += 1

    # Output: overview first, then the details from pyshacl
    print(
        f"    SHACL-Ergebnis: "
        f"{n_violations} Violation(s), "
        f"{n_warnings} Warning(s)" + (f", {n_other} sonstige" if n_other else "")
    )
    for line in results_text.splitlines():
        print(f"      {line}")

    if n_violations > 0:
        # Hard fail - there are structural problems in the bundle
        return False

    # Warnings only: the bundle counts as valid, notes are audit material
    print()
    print("    ⚠  Warnings only - bundle counts as valid.")
    return True


# ---------------------------------------------------------------------------
# Sanity Checks
# ---------------------------------------------------------------------------


def sanity_report(g: Graph) -> None:
    print("\n  ▶ Sanity-Report ...")

    n_triples = len(g)
    n_subjects = len(set(g.subjects()))
    classes = Counter(
        o for _, _, o in g.triples((None, RDF.type, None)) if isinstance(o, URIRef)
    )
    properties = Counter(p for _, p, _ in g)

    print(f"    Triples:         {n_triples:,}")
    print(f"    Subjekte:        {n_subjects:,}")
    print(f"    Distinkte Typen: {len(classes):,}")
    print(f"    Distinkte Props: {len(properties):,}")

    print("\n    Top 10 classes by instance count:")
    for cls, count in classes.most_common(10):
        print(f"      {count:>6,}  {cls}")

    print("\n    Top 10 properties by occurrence:")
    for prop, count in properties.most_common(10):
        print(f"      {count:>6,}  {prop}")


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------


def run_bundle_step(
    script_dir: Path,
    ontology_dir: Path,
    rdf_dirs: Iterable[Path],
    dist_dir: Path | None = None,
    formats: Iterable[str] = DEFAULT_BUNDLE_FORMATS,
) -> bool:
    """Build + validate. True only if the bundle was built AND all hard
    checks are ok (CRM coverage, SHACL).
    """
    if dist_dir is None:
        dist_dir = script_dir / "dist"

    # Base name without extension; build_bundle appends the right one per format.
    bundle_path = dist_dir / "geo-lod-bundle.ttl"
    g = build_bundle(ontology_dir, rdf_dirs, bundle_path, formats=formats)
    if g is None:
        return False

    crm_ok = validate_crm_coverage(g)
    shacl_ok = validate_shacl(g, ontology_dir)
    sanity_report(g)

    print()
    print(f"    CRM-Coverage:   {'✓' if crm_ok   else '✗'}")
    print(f"    SHACL:          {'✓' if shacl_ok else '✗'}")
    return crm_ok and shacl_ok


# ---------------------------------------------------------------------------
# Site bundle: one cave, handed to a consumer repository
# ---------------------------------------------------------------------------
# What a repository of the wdttest family needs is one cave and the vocabulary
# to read it, not the whole graph. The cut for that is made twice and in two
# places, and the division of labour matters:
#
#   sisal_rdf.py --sites spannagel   decides which rows become triples
#   bundle_rdf.py --sites spannagel  decides which of those triples travel
#
# This function does the second half only. It refuses to run on a graph that
# holds more than one cave with data, because a bundle named after one site
# and holding five is the kind of file nobody checks twice.
#
# The profile is "slim": the competing chronologies stay out, as they do in
# every development bundle, and so do the age assignment nodes and their time
# positions. Nothing is lost for a figure or a query page - sisal_rdf.py
# materialises the leading age on the sample itself, exactly so that
#
#   ?s geolod:ageChronology trs:SISALv3-lin_interp ; geolod:ageKaBP ?age .
#
# answers without a join. What is lost is the ability to ask which model an
# age came from through the assignment node; the property geolod:ageChronology
# on the sample still says it.
#
# The MIS vocabulary travels whole. Spannagel touches a part of it, and a
# vocabulary cut to one site would be a private variant of something published
# under w3id - the 564 KB are not worth that.

SISAL_NS = "http://w3id.org/geo-lod/sisal/"
TIME_NS = Namespace("http://www.w3.org/2006/time#")
GEOSPARQL_NS = Namespace("http://www.opengis.net/ont/geosparql#")
SF_NS = Namespace("http://www.opengis.net/ont/sf#")

#: Dropped by the slim profile, but only in the SISAL instance namespace:
#: time:TimePosition is also what the MIS vocabulary hangs its stage
#: boundaries on, and those stay.
SLIM_DROP_CLASSES: tuple[URIRef, ...] = (
    GEO_LOD["AgeAssignment"],
    TIME_NS["TimePosition"],
)


def _plain(text: str) -> str:
    """Lower case and without accents, for matching a name on the command line."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(text).strip().lower())
                   if not unicodedata.combining(c))


def _drop_nodes(g: Graph, nodes: Iterable[URIRef]) -> int:
    """Remove every triple in which one of *nodes* stands as subject or object."""
    removed = 0
    for node in nodes:
        for triple in list(g.triples((node, None, None))):
            g.remove(triple)
            removed += 1
        for triple in list(g.triples((None, None, node))):
            g.remove(triple)
            removed += 1
    return removed


def _drop_orphans(g: Graph, classes: Iterable[URIRef]) -> int:
    """Drop nodes of *classes* that nothing points at any more.

    The geometries of the 364 caves the bundle does not carry: they are their
    own nodes, and removing the cave leaves them behind as a sf:Point that
    belongs to nothing.
    """
    doomed = [node for cls in classes for node in g.subjects(RDF.type, cls)
              if not any(g.triples((None, None, node)))]
    return _drop_nodes(g, doomed)


def resolve_site_cave(g: Graph, spec: str) -> tuple[URIRef, str]:
    """The one cave this graph carries data for, checked against *spec*."""
    with_data = {cave for cave in g.objects(None, GEO_LOD["extractedFrom"])}
    if not with_data:
        raise SystemExit(
            "  ✗ no cave in SISAL/rdf carries a speleothem. Build the site "
            "graph first:\n"
            "      python SISAL/sisal_rdf.py --format turtle --sites <site>")

    labels = {cave: str(next(g.objects(cave, RDFS.label), cave)) for cave in with_data}
    if len(with_data) > 1:
        listing = ", ".join(sorted(labels.values()))
        raise SystemExit(
            f"  ✗ SISAL/rdf holds {len(with_data)} caves with data ({listing}).\n"
            f"    A site bundle is built from a single-site graph. Run:\n"
            f"      python SISAL/sisal_rdf.py --format turtle --sites {spec}")

    cave = next(iter(with_data))
    label = labels[cave]
    if not _plain(label).startswith(_plain(spec)) and _plain(spec) not in str(cave).lower():
        raise SystemExit(
            f"  ✗ SISAL/rdf holds {label!r}, not {spec!r}. Rebuild the site "
            f"graph:\n"
            f"      python SISAL/sisal_rdf.py --format turtle --sites {spec}")
    return cave, label


def build_site_bundle(
    ontology_dir: Path,
    sisal_rdf_dir: Path,
    dist_dir: Path,
    site_spec: str,
    formats: Iterable[str] = ("turtle",),
) -> Graph | None:
    """One cave, slim profile, ontology and vocabulary whole."""
    print(f"\n  ▶ Site bundle for {site_spec!r} ...")

    ontology_files = _collect_ttl_files([ontology_dir, ontology_dir / "vocab"])
    # release=True so that the collector neither skips the chronologies nor
    # points at --bundle-format release for them: they are dropped here on
    # purpose and for a different reason, and one message per decision is
    # enough.
    instance_files = _collect_ttl_files([sisal_rdf_dir], release=True,
                                        suffixes=INSTANCE_SUFFIXES)
    instance_files = _dedupe_core_copies(instance_files, ontology_dir)
    left_out = [f for f in instance_files
                if f.name in AGGREGATE_FILENAMES or f.stem in RELEASE_ONLY_STEMS]
    instance_files = [f for f in instance_files if f not in left_out]
    for f in left_out:
        print(f"    ~ {f.name} bleibt draussen (schlankes Profil)")
    if not instance_files:
        print(f"  ✗ No instance files in {sisal_rdf_dir}.")
        return None

    g = Graph()
    g.bind("crm", Namespace(CRM_FAMILY_PREFIXES[0]))
    g.bind("crmsci", Namespace("http://www.ics.forth.gr/isl/CRMsci/"))
    g.bind("crmarchaeo", Namespace("http://www.cidoc-crm.org/extensions/crmarchaeo/"))
    g.bind("geo-lod", GEO_LOD)
    g.bind("time", TIME_NS)

    print("\n  ▶ Parse & merge ...")
    for f in ontology_files + instance_files:
        added, file_triples, _ = _parse_with_repair(g, f)
        print(f"    + {f.name}: {file_triples:>8,} Triples")

    before = len(g)
    cave, label = resolve_site_cave(g, site_spec)
    print(f"\n  ▶ Trimming to {label} ...")

    other_caves = [c for c in g.subjects(RDF.type, GEO_LOD["Cave"]) if c != cave]
    dropped_catalogue = _drop_nodes(g, other_caves)
    dropped_catalogue += _drop_orphans(g, (GEOSPARQL_NS["Geometry"], SF_NS["Point"]))
    print(f"    − Catalogue: {len(other_caves)} further caves, "
          f"{dropped_catalogue:,} Triples")

    slim_nodes = [node for cls in SLIM_DROP_CLASSES
                  for node in g.subjects(RDF.type, cls)
                  if str(node).startswith(SISAL_NS)]
    dropped_slim = _drop_nodes(g, slim_nodes)
    print(f"    − schlankes Profil: {len(slim_nodes):,} Knoten "
          f"(geolod:AgeAssignment, time:TimePosition), {dropped_slim:,} Triples")

    note = (f"Site bundle: {label} only, slim profile. The competing "
            f"chronologies, the age assignment nodes and their time positions "
            f"are left out; the leading age is on the sample itself as "
            f"geolod:ageKaBP with geolod:ageChronology. The cave catalogue is "
            f"reduced to this one site. Ontology and MIS vocabulary are "
            f"complete. Derived from the geo-lod SISAL graph, not a "
            f"replacement for it.")
    g.add((GEO_LOD["SISAL_Dataset"], OWL.versionInfo, Literal(note, lang="en")))

    print(f"    = {len(g):,} Triples, from {before:,}")

    dist_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", _plain(site_spec)).strip("-")
    output_path = dist_dir / f"{slug}-bundle.ttl"

    for key in formats:
        if key not in BUNDLE_FORMATS:
            print(f"    ⚠  Unknown format skipped: {key}")
            continue
        rdflib_format, suffix, description = BUNDLE_FORMATS[key]
        target = output_path.with_suffix(suffix)
        t_start = time.perf_counter()
        g.serialize(destination=target, format=rdflib_format, encoding="utf-8")
        print(f"  ✓ {target.name:<26} {target.stat().st_size / 1048576:6.1f} MB  "
              f"{time.perf_counter() - t_start:5.1f}s  ({description})")
    return g


def run_site_bundle_step(
    script_dir: Path,
    ontology_dir: Path,
    site_spec: str,
    formats: Iterable[str] = ("turtle",),
) -> bool:
    """Build and validate. The file leaves the repository, so it is checked."""
    g = build_site_bundle(ontology_dir, script_dir / "SISAL" / "rdf",
                          script_dir / "dist", site_spec, formats)
    if g is None:
        return False

    crm_ok = validate_crm_coverage(g)
    shacl_ok = validate_shacl(g, ontology_dir)
    sanity_report(g)

    print()
    print(f"    CRM-Coverage:   {'✓' if crm_ok   else '✗'}")
    print(f"    SHACL:          {'✓' if shacl_ok else '✗'}")
    return crm_ok and shacl_ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--sites", dest="site_spec", default=None,
        help="Build a site bundle instead of the overall bundle, e.g. "
             "--sites spannagel. Requires a graph that "
             "SISAL/sisal_rdf.py --sites <the same site> has written, "
             "and writes dist/<site>-bundle.ttl.")
    parser.add_argument(
        "--format", dest="formats", default=None,
        help="Output formats, comma-separated. Available: "
             + ", ".join(BUNDLE_FORMATS)
             + ". Default: nt for the overall bundle, turtle for a "
               "site bundle.")
    args = parser.parse_args()

    here = Path(__file__).parent.absolute()
    ontology_dir = here / "ontology"

    if args.formats:
        formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    else:
        formats = ["turtle"] if args.site_spec else list(DEFAULT_BUNDLE_FORMATS)

    if args.site_spec:
        ok = run_site_bundle_step(here, ontology_dir, args.site_spec, formats)
        return 0 if ok else 1

    rdf_dirs = [
        here / "EPICA" / "rdf",
        here / "SISAL" / "rdf",
        here / "CI" / "rdf",
    ]
    ok = run_bundle_step(here, ontology_dir, rdf_dirs, formats=formats)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())
