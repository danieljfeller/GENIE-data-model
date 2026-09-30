# GDM v1.0.1

Release directory for version 1.0.1 of the GENIE Data Model. The REDCap project this release
was exported from is named "GDM - v1.0" (REDCap 16.1.4, export dated 2026-04-16); the curation
directives were prepared 2026-02-23.

## Files

| File | Source | Notes |
|---|---|---|
| [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) | Generated from the CSV by [`scripts/build_data_dictionary.py`](../scripts/build_data_dictionary.py) | All 14 instruments, 663 fields. Regenerate rather than edit. |
| [`SPECIFICATION.md`](SPECIFICATION.md) | Hand-written | Prose reference for the principal tables. See its coverage note for what it does and does not describe. |
| [`GDM_v1.0.1_DataDictionary.csv`](GDM_v1.0.1_DataDictionary.csv) | REDCap "Data Dictionary" export | **Authoritative schema.** UTF-8 with BOM. Some cells (the NCI Thesaurus drug list) exceed 128 KB, so raise your CSV parser's field-size limit. |
| [`GDM_v1.0.1_XML.xml`](GDM_v1.0.1_XML.xml) | REDCap CDISC ODM 1.3.1 export | Metadata only, no records. 11 MB. Contains the repeating-instrument configuration that the CSV lacks. |
| [`GDM_v1.0.1_CurationDirectives.pdf`](GDM_v1.0.1_CurationDirectives.pdf) | Curation manual | 259 pages, one entry per variable: definition, source documents, step-by-step curation instructions, notes. |

## Reading the CSV

The CSV has the standard 18 REDCap data-dictionary columns. The ones that matter for
implementation:

| Column | Use |
|---|---|
| `Variable / Field Name` | Column name in exports |
| `Form Name` | Table the field belongs to |
| `Field Type` | `text`, `dropdown`, `radio`, `checkbox`, `yesno`, `calc`, `notes` |
| `Choices, Calculations, OR Slider Labels` | `code, label \| code, label …` for coded fields; the formula for `calc` fields |
| `Text Validation Type OR Show Slider Number` | `date_mdy`, `number`, `integer`, `autocomplete`… |
| `Identifier?` | `y` marks PHI that must not be shared |
| `Branching Logic (Show field only if...)` | Condition under which the field is populated |
| `Required Field?` | `y` if the field must be populated when shown |
| `Field Annotation` | `@READONLY` marks Tier1A values piped in from the GENIE release |

Minimal Python that reads it safely:

```python
import csv, sys
csv.field_size_limit(sys.maxsize)
with open("GDM_v1.0.1_DataDictionary.csv", encoding="utf-8-sig", newline="") as fh:
    fields = list(csv.DictReader(fh))
```

## Instrument repeat configuration

From the ODM export. Repeating instruments produce one row per event; the others produce one
row per patient.

| Repeating (one row per event) | Once per patient |
|---|---|
| `cancer_diagnosis`, `imaging`, `clinical_visits`, `surgical_procedures`, `drug_exposure`, `clinical_trial_history`, `tumor_sample_information`, `hospitalizations` | `patient_curation_eligibility`, `cancer_patient_information`, `family_history`, `comorbidities`, `radiation_treatment`, `laboratory_testing` |

`radiation_treatment` and `laboratory_testing` are labelled "one form per treatment / result"
in their section headers but are not configured as repeating in this release. Implementers who
need multiple rows per patient for these should confirm the intended grain with the GENIE
coordinating center.

## Known gaps in this release's documentation

- `SPECIFICATION.md` covers 8 of the 14 curated instruments and does not describe
  `family_history`, `comorbidities`, `clinical_trial_history`, `radiation_treatment`,
  `hospitalizations` or `laboratory_testing`. Use `DATA_DICTIONARY.md` for those.
- The eligibility instrument and one hospitalization section header refer to a Chordoma
  study; the instrument is study-agnostic and these are cohort-specific configuration.
- The curation directives PDF describes `curation_cohort` values as "Study 1/2/3" while the
  CSV lists a single value. Treat the cohort list as site-configured.
