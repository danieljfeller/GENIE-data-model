# GENIE Logical Model diagrams

These SVGs describe the **GENIE Logical Model**: a conceptual entity-relationship view of the
oncology domain that the GDM REDCap instrument implements. Open
[`index.svg`](index.svg) for the full entity map, then the per-entity files for attributes.

The logical model is *not* a one-to-one picture of the fourteen physical GDM tables. It
names finer-grained entities (for example `visit_detail`, `report_section`, `death_cause`,
`line_of_therapy`) that the v1.0.1 instrument folds into a single form or does not yet
capture. Use it to understand intent and relationships; use the
[data dictionary](../GDM_v1.0.1/DATA_DICTIONARY.md) for what to populate.

## Entities with a diagram

| Logical entity | Diagram | Closest GDM v1.0.1 table |
|---|---|---|
| patient | [`patient.svg`](patient.svg) | `cancer_patient_information` |
| death, death_cause | [`death.svg`](death.svg), [`death_cause.svg`](death_cause.svg) | `cancer_patient_information` (vital status fields) |
| condition, cancer_condition | [`condition.svg`](condition.svg), [`cancer_condition.svg`](cancer_condition.svg) | `cancer_diagnosis`, `comorbidities` |
| visit, visit_detail | [`visit.svg`](visit.svg), [`visit_detail.svg`](visit_detail.svg) | `clinical_visits`, `hospitalizations` |
| medication | [`medication.svg`](medication.svg) | `drug_exposure` |
| procedure, therapeutic_procedure | [`procedure.svg`](procedure.svg), [`therapeutic_procedure.svg`](therapeutic_procedure.svg) | `surgical_procedures`, `radiation_treatment` |
| imaging, imaging_result | [`imaging.svg`](imaging.svg), [`imaging_result.svg`](imaging_result.svg) | `imaging` |
| specimen, cancer_specimen | [`specimen.svg`](specimen.svg), [`cancer_specimen.svg`](cancer_specimen.svg) | `tumor_sample_information` |
| genomic | [`genomic.svg`](genomic.svg) | Tier1A mutation data; `tumor_sample_information` |
| laboratory_result | [`laboratory_result.svg`](laboratory_result.svg) | `laboratory_testing` |
| observation | [`observation.svg`](observation.svg) | ECOG, biomarkers and other assessments spread across forms |
| report, report_section, pathology_report | [`report.svg`](report.svg), [`report_section.svg`](report_section.svg), [`pathology_report.svg`](pathology_report.svg) | `surgical_procedures`, `imaging` |
| order | [`order.svg`](order.svg) | ordering-institution fields on treatment tables |
| cohort, cohort_definition | [`cohort.svg`](cohort.svg), [`cohort_definition.svg`](cohort_definition.svg) | `patient_curation_eligibility` |
| organization, site, location, provider | [`organization.svg`](organization.svg), [`site.svg`](site.svg), [`location.svg`](location.svg), [`provider.svg`](provider.svg) | `center` and `*_institution` fields |

Entities that appear on the index map without their own diagram (`drug_regimen`,
`line_of_therapy`, `clinical_stage`, `pathological_stage`, `performance_status`,
`histology_morphology_behavior`, `disease_status`, `study`, `data_set` and others) are
modelled as attributes of the tables above in v1.0.1.

`observation copy.svg` is a duplicate of `observation.svg` retained from the original upload.
