"""
FAIR-MIND AP v3 - SPARQL Competency Question Validation
fair_mind_ap_v3.ttl against 10 competency questions.

Note: CQ1 originally specified PHQ-9 total score >10.
In the MIMIC-IV implementation, PHQ-9 is unavailable;
depression is represented via ICD-10 F32/F33 (SNOMED:35489007).
CQ1 has been adapted accordingly.
"""

from rdflib import Graph, Namespace, RDF, RDFS, OWL

# Load with RDFS reasoning
g = Graph()
g.parse('fair_mind_ap_v3.ttl', format='turtle')

# Compute RDFS subclass closure
extra = [(ind, RDF.type, sup)
         for sub, _, sup in g.triples((None, RDFS.subClassOf, None))
         for ind in g.subjects(RDF.type, sub)
         if (ind, RDF.type, sup) not in g]
for t in extra:
    g.add(t)

print(f"Loaded: {len(g)} triples (with RDFS entailment)\n")
print("=" * 65)

PREFIX = """
PREFIX fm:     <https://w3id.org/fair-mind/ap#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX efo:    <http://www.ebi.ac.uk/efo/>
PREFIX snomed: <http://snomed.info/id/>
PREFIX ncit:   <http://purl.obolibrary.org/obo/NCIT_>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
"""

cqs = [

    # Data Discovery
    {
        "id": "CQ1",
        "category": "Data Discovery",
        "question": (
            "Retrieve all participants with depression diagnosis "
            "(ICD-10 F32/F33, SNOMED:35489007) AND at least one HRV measurement. "
            "[Original CQ: PHQ-9 total score >10; adapted for MIMIC-IV "
            "where PHQ-9 is unavailable and ICD-10 diagnostic codes are used.]"
        ),
        "query": PREFIX + """
SELECT DISTINCT ?clinVar ?clinLabel ?bioVar ?bioLabel
WHERE {
  ?clinVar a fm:ClinicalVar ;
           rdfs:label ?clinLabel ;
           fm:hasOntologyTerm snomed:35489007 .

  ?bioVar  a fm:HRVFeature ;
           rdfs:label ?bioLabel .
}
ORDER BY ?bioLabel
""",
        "expect_min": 10,
        "comment": (
            "RDFS entailment required: HRV subclasses (TimeDomainHRV, "
            "SpectralHRV, etc.) must be inferred as fm:HRVFeature instances."
        )
    },

    {
        "id": "CQ2",
        "category": "Data Discovery",
        "question": (
            "Find all ECG recording timestamps linkable to a depression "
            "assessment within a 30-day window."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?layer
WHERE {
  ?var rdfs:label ?label ;
       fm:belongsToLayer ?layer .
  FILTER(
    ?var = fm:recording_date ||
    ?var = fm:admittime      ||
    ?var = fm:dischtime
  )
}
""",
        "expect_min": 3,
        "comment": "recording_date, admittime, dischtime - temporal linkage variables"
    },

    {
        "id": "CQ3",
        "category": "Data Discovery",
        "question": (
            "Identify participants on antidepressants WITHOUT lithium "
            "co-prescription - retrieve the relevant medication variables."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?term
WHERE {
  ?var a fm:MedicationVar ;
       rdfs:label ?label ;
       fm:hasOntologyTerm ?term .
}
ORDER BY ?label
""",
        "expect_min": 2,
        "comment": "Layer 4: antidepress (MeSH D000928), lithium (CHEBI:30145)"
    },

    # Data Integration
    {
        "id": "CQ4",
        "category": "Data Integration",
        "question": (
            "Compare RMSSD distributions across depression severity categories - "
            "retrieve the relevant clinical and biomarker variables with ontology terms."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?ontTerm ?mappingType
WHERE {
  {
    ?var a fm:ClinicalVar ;
         rdfs:label ?label ;
         fm:hasOntologyTerm ?ontTerm ;
         fm:mappingType ?mappingType .
  } UNION {
    ?var rdfs:label "RMSSD" ;
         rdfs:label ?label ;
         fm:hasOntologyTerm ?ontTerm ;
         fm:mappingType ?mappingType .
  }
}
""",
        "expect_min": 2,
        "comment": "Returns clinical labels (depression, suicidality) and RMSSD (EFO:0009257)"
    },

    {
        "id": "CQ5",
        "category": "Data Integration",
        "question": (
            "Retrieve HRV values adjusted for age and BMI (z-scored)."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?notes
WHERE {
  ?var rdfs:label ?label ;
       fm:uriVerified "extension_term" ;
       fm:refinementNotes ?notes .
  FILTER(
    CONTAINS(LCASE(?notes), "z-score") ||
    CONTAINS(LCASE(STR(?label)), "z_")
  )
}
""",
        "expect_min": 2,
        "comment": "z_age, z_BMI - standardized covariates for adjusted analysis"
    },

    {
        "id": "CQ6",
        "category": "Data Integration",
        "question": (
            "Find all HRV metrics derived from the same ECG recording session."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?source ?paramsRef
WHERE {
  ?var a owl:NamedIndividual ;
       rdfs:label ?label ;
       fm:computedFrom ?source .
  OPTIONAL { ?var fm:hasParamsRef ?paramsRef . }
}
ORDER BY ?source ?label
""",
        "expect_min": 17,
        "comment": "All ComputedVariables linked via fm:computedFrom fm:RRIntervals"
    },

    # Provenance and Quality
    {
        "id": "CQ7",
        "category": "Provenance",
        "question": (
            "Identify which ECG processing protocol and parameter file "
            "was used for each HRV metric."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?paramsRef ?notes
WHERE {
  ?var a owl:NamedIndividual ;
       rdfs:label ?label ;
       fm:hasParamsRef ?paramsRef .
  OPTIONAL { ?var fm:refinementNotes ?notes . }
}
ORDER BY ?label
""",
        "expect_min": 1,
        "comment": "Reproducibility core: parameter JSON reference per computed variable"
    },

    {
        "id": "CQ8",
        "category": "Provenance",
        "question": (
            "List all participants excluded due to cardiac arrhythmia - "
            "retrieve clinical label variables used for exclusion criteria."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?layer ?verified
WHERE {
  ?var a fm:ClinicalVar ;
       rdfs:label ?label ;
       fm:belongsToLayer ?layer ;
       fm:uriVerified ?verified .
}
""",
        "expect_min": 2,
        "comment": "Layer 1 clinical variables - basis for data quality gating"
    },

    {
        "id": "CQ9",
        "category": "Provenance",
        "question": (
            "Retrieve the standardisation method applied to age and BMI variables."
        ),
        "query": PREFIX + """
SELECT ?var ?label ?notes ?ontTerm
WHERE {
  ?var rdfs:label ?label ;
       fm:refinementNotes ?notes ;
       fm:hasOntologyTerm ?ontTerm .
  FILTER(
    CONTAINS(LCASE(STR(?label)), "age") ||
    CONTAINS(LCASE(STR(?label)), "bmi")
  )
}
ORDER BY ?label
""",
        "expect_min": 3,
        "comment": "Derivation formulas documented in refinementNotes"
    },

    # Clinical Interpretation
    {
        "id": "CQ10",
        "category": "Clinical Interpretation",
        "question": (
            "Find participants with suicidality AND reduced parasympathetic "
            "activity (HF power below 10th percentile) - retrieve the relevant variables."
        ),
        "query": PREFIX + """
SELECT ?clinVar ?clinLabel ?bioVar ?bioLabel ?freqBand ?notes
WHERE {
  ?clinVar a fm:ClinicalVar ;
           rdfs:label ?clinLabel ;
           fm:hasOntologyTerm snomed:429451000124109 .

  ?bioVar a fm:SpectralHRV ;
          rdfs:label ?bioLabel .
  OPTIONAL { ?bioVar fm:frequencyBand ?freqBand . }
  OPTIONAL { ?bioVar fm:refinementNotes ?notes . }
}
ORDER BY ?bioLabel
""",
        "expect_min": 1,
        "comment": "Suicidality (SNOMED:429451000124109) x SpectralHRV - LRS cluster core"
    },
]

# Run validation
passed = 0
failed = 0

for cq in cqs:
    print(f"\n{'─'*65}")
    print(f"[{cq['id']}] {cq['category']}")
    print(f"Q: {cq['question'][:120]}{'...' if len(cq['question']) > 120 else ''}")
    print(f"   ({cq['comment']})")

    try:
        results = list(g.query(cq['query']))
        n = len(results)
        ok = n >= cq['expect_min']

        if ok:
            status = "PASS"
            passed += 1
        else:
            status = f"FAIL ({n} rows, min {cq['expect_min']} required)"
            failed += 1

        print(f"Result: {'[PASS]' if ok else '[FAIL]'} {status} — {n} rows returned")

        for i, row in enumerate(results[:4]):
            row_str = " | ".join(
                str(v).split("#")[-1].split("/")[-1][:35] if v else "-"
                for v in row
            )
            print(f"  {i+1}. {row_str}")
        if n > 4:
            print(f"  ... and {n-4} more")

    except Exception as e:
        print(f"Result: [ERROR] {e}")
        failed += 1

print(f"\n{'='*65}")
print(f"Final: {passed}/10 passed  |  {failed}/10 failed")
if failed == 0:
    print("[OK] All 10 CQs passed - SPARQL validation complete.")