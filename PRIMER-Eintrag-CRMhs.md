# PRIMER-Eintrag: CRMhs (zum Einfügen)

Stand: 2026-11-03. Quellen: Felicetti & Murano 2026 (Heritage 9(5), 186), CRMhs-Spezifikation v1.2, LODE-Doku.

---

## Teil A4 (Beschlusslage) – neuer Eintrag

**CRMhs als Kandidat für S4 (Ontology Alignment), noch nicht beschlossen.**

- Referenzen:
  - Namespace: `http://vast-lab.org/crmhs/` (Präfix `crmhs`)
  - Repo: https://github.com/vastlab-dev/CRMhs (Datei `CRMhs_Ontology_V1.2.rdfs`, Ordner `example/`)
  - Zenodo: https://doi.org/10.5281/zenodo.18956181 (im Paper steht ...182; vermutlich Concept- vs. Versions-DOI, prüfen und für Zitat die Versions-DOI nehmen)
  - Paper: https://doi.org/10.3390/heritage9050186
  - Doku: https://vast-lab.org/crmhs/
- Version 1.2, Lizenz **CC BY-NC-SA 4.0** (Ontologie selbst).
- CRMhs ist eine Erweiterung von CRMsci (HS3 Analysis ⊑ crmsci:S4_Observation; HS9 Study Object Sample ⊑ crmsci:S13_Sample), nutzt zusätzlich CRMdig (D9, D14, D8) und CRMinf.
- Grundsatz: CRMhs nur dort einsetzen, wo geo-lod Labor-/Analyse-Provenienz wirklich aus den Quelldaten belegen kann. Keine erfundenen Geräte, Protokolle oder Einstellungen (analog zur Entscheidung zu `original_chronology`).

## Teil B – neuer Schritt

| Schritt | Titel | Status |
|---|---|---|
| S4a | CRMhs-Evaluation (Mapping-Skizze, Pilot an einem SISAL-Entity) | offen, nach S3f |

## Teil C – S4a (Skizze)

Ziel: prüfen, ob ein CRMhs-Layer für SISAL (und ggf. EPICA) die Provenienzkette Entity → Probe → Analyse → Datensatz → Interpretation sauber abbildet, ohne die bestehenden Qualitätsmarken zu brechen.

Mapping-Kandidaten:

| geo-lod / Quelle | CRMhs | Anmerkung |
|---|---|---|
| Speleothem / Entity (SISAL `entity`) | `HS6` Study Object (über E18/E19) | Entity ist natürlicher Körper; Typisierung als E19 prüfen |
| Probenposition (`depth_sample`) | `HS8` Study Object Area + `HSP21` (E94 Space Primitive) | 1D-Tiefe entlang der Wachstumsachse |
| Probe (U-Th, δ18O/δ13C) | `HS9` Study Object Sample, `HSP19` was taken from, `HSP20` was taken from area | |
| Datierung / Isotopenmessung | `HS3` Analysis, `HSP4` analysed, `HSP16` produced dataset | HS3 ⊑ S4 und damit anschlussfähig an SOSA/SSN-Mapping |
| Messreihen, Datierungstabellen | `HS13` Scientific Dataset | ⊑ D9 Data Object |
| Altersmodell (StalAge, COPRA, Bacon, ...) | `HS1` Scientific Activity + `HSP10` used software (D14) + `HSP12` used dataset | Altersmodell-Rechnung ist keine Messung, daher HS1 statt HS3 |
| Messgerät, Settings, Protokoll | `HS11`, `HS14`, `HS5`, `HSP7/HSP8/HSP13` | nur wenn in SISAL/Quellpublikation belegt |
| MIS-Zuordnung (`assignmentStatus`, `leadingSource`) | CRMinf `I7` Belief Adoption → `I12`, `J7` is evidence for | Muster aus dem Paper (Fallstudie 1); Abgleich mit MIS-Vokabular-Entscheidung |
| EPICA-Kern | `HS6` / `HS7` Portion; Analysen als `HS3` | Quelle liefert meist nur verarbeitete Tabellen, Nutzen begrenzt |
| CI-Fundstellen | voraussichtlich nicht relevant | höchstens für Datierungen der Fundstellen |

Noch zu klären (siehe Teil D):

- CRMdig als neue Abhängigkeit im Ontologie-Stack.
- Auswirkung auf SHACL-Gate und CRM-Coverage-Test (30/30, 60/60): HS-Klassen bräuchten eine eigene Coverage-Zeile.
- Byte-Stabilität: nur deterministische IRIs, `geo_lod_release.py` wie gehabt.

## Teil D – offene Punkte

1. **Lizenz**: CRMhs ist CC BY-NC-SA 4.0. Nur Referenzieren der IRIs ist unkritisch; Kopieren/Einbetten der Ontologie in `dist/*-bundle.ttl` oder `geo_lod_core.ttl` wäre mit der Lizenz der geo-lod-Artefakte abzugleichen (NC + SA). Vorschlag: nur per IRI referenzieren, Ontologie nicht mitliefern.
2. **Zenodo-DOI**: ...181 (Flo) vs. ...182 (Paper) klären.
3. **E18 ⊑ HS6**: CRMhs deklariert E18 als Subklasse von HS6. Mit importierter Ontologie wäre jedes E18 ein Study Object; Reasoner/SHACL-Effekte testen, bevor wir importieren.
4. **Persistenz**: Namespace liegt auf `vast-lab.org`, nicht auf w3id. Dereferenzierbarkeit vor Release prüfen.
5. **Spezifikation inkonsistent** (nur Doku, keine IRIs betroffen): 4.2.1.4 nennt "HSP18 has maker" (richtig: HSP22); 5.1.4 nennt "HSP5 was prepared by" (richtig: HSP5 prepared); HSP20-Scope-Note verweist auf "HSP18 was taken from" (richtig: HSP19); Fig. 2 beschriftet "HP17".
6. **IRI-Form** laut Paper-Listing: `crmhs:HS3_Analysis`, `crmhs:HSP4_analysed` (Unterstriche); in der LODE-Doku genauso. Beim Mapping so übernehmen.
7. Entscheidung, ob `wdttest-*`-Konsumenten CRMhs mitbekommen oder nur geo-lod es produziert (Architekturgrundsatz: geo-lod ist alleiniger Producer).
