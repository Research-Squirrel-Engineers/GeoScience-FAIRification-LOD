"""Superclass spine of the CIDOC CRM family classes that anchor geo-lod, up to crm:E1_CRM_Entity.

An excerpt for drawing, not the CRM: one primary parent per class (CRM allows several, e.g. E18 also sits under E92).
Sources: CIDOC CRM 7.1 class hierarchy, CRMsci 2.0, CRMarchaeo 1.x (A2, A3 -> A8 -> S20 -> E26), CRMgeo 1.2.
Add a class here when a new bridging axiom reaches one that is missing; build_crosswalk reports it otherwise."""
from __future__ import annotations

CRM = "http://www.cidoc-crm.org/cidoc-crm/"
SCI = "http://www.ics.forth.gr/isl/CRMsci/"
GEO = "http://www.ics.forth.gr/isl/CRMgeo/"
ARC = "http://www.cidoc-crm.org/extensions/crmarchaeo/"

E1 = CRM + "E1_CRM_Entity"

_P = {  # class -> primary parent
    CRM + "E2_Temporal_Entity": "E1_CRM_Entity",
    CRM + "E4_Period": "E2_Temporal_Entity",
    CRM + "E5_Event": "E4_Period",
    CRM + "E7_Activity": "E5_Event",
    CRM + "E13_Attribute_Assignment": "E7_Activity",
    CRM + "E77_Persistent_Item": "E1_CRM_Entity",
    CRM + "E70_Thing": "E77_Persistent_Item",
    CRM + "E71_Human-Made_Thing": "E70_Thing",
    CRM + "E72_Legal_Object": "E70_Thing",
    CRM + "E18_Physical_Thing": "E72_Legal_Object",
    CRM + "E19_Physical_Object": "E18_Physical_Thing",
    CRM + "E20_Biological_Object": "E19_Physical_Object",
    CRM + "E21_Person": "E20_Biological_Object",
    CRM + "E24_Physical_Human-Made_Thing": "E18_Physical_Thing",
    CRM + "E22_Human-Made_Object": "E24_Physical_Human-Made_Thing",
    CRM + "E26_Physical_Feature": "E18_Physical_Thing",
    CRM + "E27_Site": "E26_Physical_Feature",
    CRM + "E78_Curated_Holding": "E24_Physical_Human-Made_Thing",
    CRM + "E28_Conceptual_Object": "E71_Human-Made_Thing",
    CRM + "E55_Type": "E28_Conceptual_Object",
    CRM + "E89_Propositional_Object": "E28_Conceptual_Object",
    CRM + "E73_Information_Object": "E89_Propositional_Object",
    CRM + "E29_Design_or_Procedure": "E73_Information_Object",
    CRM + "E31_Document": "E73_Information_Object",
    CRM + "E32_Authority_Document": "E31_Document",
    CRM + "E39_Actor": "E77_Persistent_Item",
    CRM + "E53_Place": "E1_CRM_Entity",
    CRM + "E54_Dimension": "E1_CRM_Entity",
    SCI + "S4_Observation": "E13_Attribute_Assignment",
    SCI + "S6_Data_Evaluation": "E13_Attribute_Assignment",
    SCI + "S1_Matter_Removal": "E5_Event",
    SCI + "S13_Sample": "E18_Physical_Thing",
    SCI + "S9_Property_Type": "E55_Type",
    SCI + "S20_Rigid_Physical_Feature": "E26_Physical_Feature",
    ARC + "A8_Stratigraphic_Unit": "S20_Rigid_Physical_Feature",
    ARC + "A2_Stratigraphic_Volume_Unit": "A8_Stratigraphic_Unit",
    ARC + "A3_Stratigraphic_Interface": "A8_Stratigraphic_Unit",
    GEO + "SP6_Declarative_Place": "E53_Place",
}


def _full(local: str) -> str:
    for ns in (CRM, SCI, ARC, GEO):
        if ns + local in _P or (ns + local == E1):
            return ns + local
    raise KeyError(local)


PARENT = {k: _full(v) for k, v in _P.items()}


def up(iri: str) -> list[str]:
    """[iri, parent, ..., E1]; just [iri] when the class is not in the table (the figure then marks the gap)."""
    out = [iri]
    while out[-1] != E1 and out[-1] in PARENT:
        out.append(PARENT[out[-1]])
    return out


def reaches_e1(iri: str) -> bool:
    return up(iri)[-1] == E1
