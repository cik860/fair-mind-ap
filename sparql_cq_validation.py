"""
FAIR-MIND AP v4 — Schema-Level CQ Validation
=============================================
Validates 10 competency questions against the AP schema (TTL file).
Uses rdflib with RDFS entailment for subclass inference.

This script validates the AP DESIGN — that the schema defines the right
variables, types, and relationships to answer each CQ.
Instance-level validation (against real data) is separate.
"""
from rdflib import Graph, RDF, RDFS, OWL, Namespace
import os

# Load AP
TTL_PATH = os.path.join(os.path.dirname(__file__), "fair_mind_ap_v3.ttl")

g = Graph()
g.parse(TTL_PATH, format="turtle")

# RDFS entailment: subClassOf closure
triples_to_add = []
for s, p, o in g.triples((None, RDFS.subClassOf, None)):
    for inst in g.subjects(RDF.type, s):
        triples_to_add.append((inst, RDF.type, o))
for t in triples_to_add:
    g.add(t)

FM = Namespace("https://w3id.org/fair-mind/ap#")

PRE = """
PREFIX fm:     <https://w3id.org/fair-mind/ap#>
PREFIX efo:    <http://www.ebi.ac.uk/efo/>
PREFIX ncit:   <http://purl.obolibrary.org/obo/NCIT_>
PREFIX snomed: <http://snomed.info/id/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX sosa:   <http://www.w3.org/ns/sosa/>
"""

CQS = {
    "CQ1": {
        "category": "Data Discovery",
        "question": "Find variables for participants with depression AND HRV measurement",
        "query": PRE + """
SELECT DISTINCT ?clinVar ?bioVar WHERE {
  ?clinVar a snomed:35489007 .
  ?bioVar a fm:HRVFeature .
}""",
    },
    "CQ2": {
        "category": "Data Discovery",
        "question": "Find timestamp variables for temporal linkage with depression assessment",
        "query": PRE + """
SELECT ?var ?label WHERE {
  ?var a fm:Timestamp ; rdfs:label ?label .
}""",
    },
    "CQ3": {
        "category": "Data Discovery",
        "question": "Find medication variables for antidepressant/lithium filtering",
        "query": PRE + """
SELECT ?var ?label WHERE {
  ?var a fm:MedicationVar ; rdfs:label ?label .
}""",
    },
    "CQ4": {
        "category": "Data Integration",
        "question": "Find RMSSD and depression variables for group comparison",
        "query": PRE + """
SELECT ?clinLabel ?bioLabel WHERE {
  ?clin a snomed:35489007 ; rdfs:label ?clinLabel .
  ?bio a efo:EFO_0009257 ; rdfs:label ?bioLabel .
}""",
    },
    "CQ5": {
        "category": "Data Integration",
        "question": "Find age and BMI covariate variables",
        "query": PRE + """
SELECT ?var ?label ?comment WHERE {
  ?var a fm:DemographicVar ; rdfs:label ?label .
  OPTIONAL { ?var rdfs:comment ?comment . }
  FILTER(CONTAINS(LCASE(STR(?label)), "age") || CONTAINS(LCASE(STR(?label)), "bmi"))
}""",
    },
    "CQ6": {
        "category": "Data Integration",
        "question": "Find all HRV metrics derived from the same signal source",
        "query": PRE + """
SELECT ?label ?source WHERE {
  ?var fm:computedFrom ?source ; rdfs:label ?label .
} ORDER BY ?source ?label""",
    },
    "CQ7": {
        "category": "Provenance",
        "question": "Find processing protocol and parameters for each HRV measurement",
        "query": PRE + """
SELECT ?label ?paramsRef WHERE {
  ?var fm:hasParamsRef ?paramsRef ; rdfs:label ?label .
} ORDER BY ?label""",
    },
    "CQ8": {
        "category": "Provenance",
        "question": "Find clinical label variables for cohort inclusion/exclusion",
        "query": PRE + """
SELECT ?var ?label WHERE {
  ?var a fm:ClinicalVar ; rdfs:label ?label .
}""",
    },
    "CQ9": {
        "category": "Provenance",
        "question": "Find standardization method for age and BMI",
        "query": PRE + """
SELECT ?label ?comment WHERE {
  ?var rdfs:label ?label ; rdfs:comment ?comment .
  FILTER(CONTAINS(LCASE(STR(?label)), "z_"))
}""",
    },
    "CQ10": {
        "category": "Clinical Interpretation",
        "question": "Find suicidality + spectral HRV variables for autonomic assessment",
        "query": PRE + """
SELECT ?clinLabel ?bioLabel ?band WHERE {
  { ?clin rdfs:seeAlso snomed:429451000124109 ; rdfs:label ?clinLabel . }
  ?bio a fm:SpectralHRV ; rdfs:label ?bioLabel .
  OPTIONAL { ?bio fm:frequencyBand ?band . }
}""",
    },
}


def main():
    print("=" * 60)
    print(f"FAIR-MIND AP v4 — Schema-Level CQ Validation")
    print(f"TTL: {TTL_PATH}")
    print(f"Triples: {len(g)} (with RDFS entailment)")
    print("=" * 60)

    passed = 0
    for cq_id, cq in CQS.items():
        results = list(g.query(cq["query"]))
        n = len(results)
        ok = n > 0
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"\n[{cq_id}] {status} ({n} rows) — {cq['category']}")
        print(f"  {cq['question']}")
        for row in results[:3]:
            vals = " | ".join(str(v)[:40] for v in row)
            print(f"    -> {vals}")

    print(f"\n{'='*60}")
    print(f"Result: {passed}/10 passed")


if __name__ == "__main__":
    main()
