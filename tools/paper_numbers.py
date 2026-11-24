"""Extracts all numbers of the paper from the committed graphs of a geo-lod clone.
Usage: py -I tools/paper_numbers.py <repo> [out_dir]   ->  numbers.json, numbers.md"""
import sys, glob, json, os, subprocess
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef
repo = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else "."
GL = "http://w3id.org/geo-lod/"
G = rdflib.Graph(); per = {}
for f in sorted(glob.glob(os.path.join(repo, "*", "rdf", "*.ttl"))):
    g = rdflib.Graph(); g.parse(f); per[os.path.relpath(f, repo).replace("\\", "/")] = len(g); G += g
O = rdflib.Graph()
for f in sorted(glob.glob(os.path.join(repo, "ontology", "*.ttl"))): O.parse(f)
def one(s, g=G):
    return int(next(iter(g.query(s)))[0])
def cnt(cls): return one(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{?s a <{cls}>}}")
N = {}
N["triples_merged"] = len(G); N["triples_per_file"] = per
N["sites_with_geometry"] = one("SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {?s <http://www.opengis.net/ont/geosparql#hasGeometry> ?g}")
N["caves"] = cnt(GL+"Cave"); N["caves_screened"] = one(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{?s a <{GL}Cave>; <{GL}screenedForArchaeology> ?o}}")
N["caves_archaeological"] = cnt(GL+"ArchaeologicalCaveSite")
N["caves_unesco"] = one(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{?s <{GL}isUNESCOWorldHeritage> ?o}}")
N["caves_wikidata_sameas"] = one(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{?s a <{GL}Cave>; <{OWL.sameAs}> ?o}}")
N["samples_d18o"] = one(f"SELECT (SUM(?n) AS ?x) WHERE {{?s <{GL}countD18OSamples> ?n}}")
N["samples_d13c"] = one(f"SELECT (SUM(?n) AS ?x) WHERE {{?s <{GL}countD13CSamples> ?n}}")
N["age_control_points"] = cnt(GL+"strat/AgeControlPoint"); N["growth_hiatus"] = cnt(GL+"GrowthHiatus")
N["ci_findspots"] = cnt(GL+"CIFindspot"); N["ci_archaeological"] = cnt(GL+"CIArchaeologicalSite")
ev = URIRef(GL+"ci_volcanic_event"); crm = "http://www.cidoc-crm.org/cidoc-crm/"
N["ci_event_P12"] = len(set(G.objects(ev, URIRef(crm+"P12_occurred_in_the_presence_of"))))
N["ci_event_P7"] = len(set(G.objects(ev, URIRef(crm+"P7_took_place_at"))))
N["ci_event_has_type"] = len(list(G.objects(ev, RDF.type))); N["ci_event_has_timespan"] = len(list(G.objects(ev, URIRef(crm+"P4_has_time-span"))))
obs = {}
for r in G.query(f"SELECT ?p (COUNT(?o) AS ?n) WHERE {{?o a <{GL}IceCoreObservation>; <http://www.w3.org/ns/sosa/observedProperty> ?p}} GROUP BY ?p"):
    obs[str(r[0]).rsplit("_", 1)[-1]] = int(r[1])
N["epica_observations"] = cnt(GL+"IceCoreObservation"); N["epica_obs_by_property"] = obs
N["mis_membership_assignments"] = cnt(GL+"MISMembershipAssignment"); N["mis_attribute_assignments"] = cnt(GL+"MISAttributeAssignment")
N["sample_sections"] = cnt(GL+"SampleSection")
coll = {}
for r in G.query("SELECT ?c (COUNT(?m) AS ?n) WHERE {?c <http://www.w3.org/2000/01/rdf-schema#member> ?m} GROUP BY ?c"):
    coll[str(r[0]).replace(GL, "")] = int(r[1])
N["collections"] = coll
sys.path.insert(0, os.path.join(repo, "visuals"))
import model_data
M = model_data.Model(__import__("pathlib").Path(repo)); C = M.counts()
N["classes"] = {k: v["classes"] for k, v in C.items()}; N["classes_anchored"] = {k: v["anchored"] for k, v in C.items()}
N["properties"] = {k: v["object"] + v["datatype"] for k, v in C.items()}; N["model_check_problems"] = M.check()
N["slide_figures"] = len([f for f in glob.glob(os.path.join(repo, "docu", "img", "[0-9][0-9]-*.svg"))])
N["cluster_pages"] = len(glob.glob(os.path.join(repo, "docu", "cluster-*.html")))
try: N["commit"] = subprocess.check_output(["git", "-C", repo, "rev-parse", "--short", "HEAD"], text=True).strip()
except Exception: N["commit"] = "?"
os.makedirs(out, exist_ok=True)
json.dump(N, open(os.path.join(out, "numbers.json"), "w"), indent=1, ensure_ascii=False)
with open(os.path.join(out, "numbers.md"), "w", encoding="utf-8") as f:
    f.write(f"# Zahlen aus geo-lod @ {N['commit']}\n\n")
    for k, v in N.items(): f.write(f"- {k}: {v}\n")
print(open(os.path.join(out, "numbers.md"), encoding="utf-8").read())
