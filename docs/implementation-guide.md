# Implementing the GENIE Data Model

A practical guide for data engineers mapping an institution's clinical data into GDM v1.0.1.
It assumes you are comfortable with SQL or a dataframe library and have read the two-minute
overview in the [repository README](../README.md).

Throughout, "the dictionary" means [`DATA_DICTIONARY.md`](../GDM_v1.0.1/DATA_DICTIONARY.md),
generated from the authoritative REDCap CSV. When this guide and the dictionary disagree, the
dictionary wins.

---

## 1. Understand what you are producing

GDM output is a set of flat tables, one per REDCap instrument, sharing a patient key. You are
not required to run REDCap. You are producing tables whose column names, codes and grain match
what a REDCap export of the GDM project would contain.

### Layers

| Layer | Contents | Who produces it |
|---|---|---|
| **Tier1A (core GENIE)** | Patient, sample and mutation files already submitted to GENIE and published on Synapse and cBioPortal | The GENIE genomic submission pipeline. Not redefined by GDM. |
| **Extended GDM** | The 14 curated instruments in this repository | Your ETL, a curation team, or both |

Tier1A values reappear inside the extended tables as read-only "piped in" fields (flagged
`read-only / piped in` in the dictionary, `@READONLY` in the CSV). For example
`cancer_patient_information.patient_id`, `center`, `sex`, `primary_race` and
`ethnicity` are copied from the GENIE clinical patient file, while the `*_curated` fields
beside them are abstracted locally. Populate the piped-in fields from your GENIE submission,
not from the EHR.

### Grain and keys

| Table | Grain | Key(s) |
|---|---|---|
| `cancer_patient_information` | one row per patient | PK `patient_id_curated` |
| `family_history`, `comorbidities` | one row per patient | FK `patient_id_curated` |
| `cancer_diagnosis` | one row per diagnosis | FK `patient_id_curated`; natural key `dx_primary_site` + `dx_date_int` |
| `imaging` | one row per radiology report | FK `patient_id_curated`; natural key `imaging_date_int` |
| `clinical_visits` | one row per oncology visit | FK `patient_id_curated`; natural key `visit_date_int` |
| `surgical_procedures` | one row per pathology report | FK `patient_id_curated`; natural key `proc_date_int` |
| `drug_exposure` | one row per drug exposure | FK `patient_id_curated`; natural key `trt_start_date_int` (+ trial start) |
| `clinical_trial_history` | one row per enrollment | FK `patient_id_curated`; natural key `clinical_trial_date_int` |
| `radiation_treatment` | one row per course (see note) | FK `patient_id_curated` |
| `tumor_sample_information` | one row per sequenced sample | FK `patient_id_curated`; links to the GENIE sample ID |
| `hospitalizations` | one row per admission | FK `patient_id_curated`; natural key `hosp_start_date_int` |
| `laboratory_testing` | one row per result (see note) | FK `patient_id_curated` |
| `patient_curation_eligibility` | one row per patient | curation workflow only; usually not shared |

The natural keys above are the "custom record labels" REDCap uses to distinguish repeat
instances; they are a good default for de-duplication. `radiation_treatment` and
`laboratory_testing` are not configured as repeating instruments in v1.0.1 despite their
section headers. See the [release README](../GDM_v1.0.1/README.md).

---

## 2. Inventory your sources

Most GDM fields come from a small number of institutional systems. Mapping them up front
saves rework.

| GDM table | Typical source |
|---|---|
| `cancer_patient_information` | GENIE clinical patient file (piped in); registration/ADT for vital status and last contact; tumor registry or NDI for death |
| `cancer_diagnosis` | Tumor registry NAACCR abstract (`*_tr`, `*_trhis` fields); oncologist notes for curated staging and metastatic sites |
| `imaging` | Radiology report text or structured RIS fields |
| `clinical_visits` | Medical oncology progress notes; ECOG from flowsheets |
| `surgical_procedures` | Surgical pathology reports; synoptic (CAP) reports for site-specific items and biomarkers |
| `drug_exposure` | Pharmacy / infusion administration records; oncology treatment plans |
| `clinical_trial_history` | Clinical trial management system |
| `radiation_treatment` | Radiation oncology information system |
| `tumor_sample_information` | GENIE clinical sample file (piped in); molecular pathology LIMS |
| `hospitalizations` | ADT encounters |
| `laboratory_testing` | LIS results with LOINC |
| `comorbidities`, `family_history` | Problem list, social history, curated notes |

Fields with no structured source anywhere are the ones a curation team fills from the chart
using the [Curation Directives](../GDM_v1.0.1/GDM_v1.0.1_CurationDirectives.pdf). Deciding
early which fields are ETL-populated and which are curator-populated keeps both teams
honest about coverage.

---

## 3. Build the patient spine

Start with `cancer_patient_information`. Everything else hangs off it.

1. **Identify the cohort.** GDM is populated for patients who have a GENIE sample. Join your
   local patient list to the GENIE clinical patient file for your center.
2. **Set `patient_id_curated`** to the GENIE patient identifier, exactly as submitted to
   GENIE (`GENIE-<CENTER>-<ID>`, for example `GENIE-DFCI-000183`). Do not mint new IDs.
3. **Hold the date of birth privately.** `birth_date` is PHI and is never shared, but you need
   it for every date conversion in step 4. Keep it in a staging table that is dropped from the
   output.
4. **Populate the piped-in Tier1A fields** (`patient_id`, `center`, `sex`, `primary_race`,
   `ethnicity`, `birth_year` and so on) from the GENIE file, and the `*_curated` equivalents
   from your local systems using the NAACCR codes given in the dictionary.
5. **Derive vital status.** `dead_curated` is `1` when a death date is known and `0`
   otherwise; `death_year_curated` and `death_date_int` are populated only when `dead_curated = 1`.
   `lastalive_date_int` is the censoring date for survivors and is required.

---

## 4. Convert every date to days from birth

This is the single most important convention in GDM and the one most likely to be done
inconsistently.

**Rule.** For every calendar date `x_date`, the shared field is
`x_date_int = (x_date − birth_date)` in whole days. The calendar date itself is PHI and is
not shared.

```sql
-- PostgreSQL / DuckDB
SELECT patient_id_curated,
       (dx_date::date - birth_date::date) AS dx_date_int
FROM staging_patient_diagnosis;
```

```python
# pandas
df["dx_date_int"] = (df["dx_date"] - df["birth_date"]).dt.days
```

Check your work:

- `x_date_int` is a non-negative integer for any event after birth.
- Age in years at the event is `x_date_int / 365.25`. The dictionary defines `dx_age_yr` as
  `round([dx_date_int] / 365.25, 4)`; reproduce that exactly rather than truncating.
- Intervals between two events are simple differences: time on treatment is
  `trt_end_date_int − trt_start_date_int`.
- Every `_int` field in the dictionary has a paired `_date` field. Populate the `_int`,
  leave the `_date` out of shared output.

REDCap computes these fields itself with `datediff([birth_date],[x_date],"d","mdy",true)`;
your ETL reproduces that calculation.

---

## 5. Map tables in dependency order

Tables that only need the patient spine can be built in parallel. Tables that reference a
diagnosis or a sample come last.

| Phase | Tables | Depends on |
|---|---|---|
| 1 | `cancer_patient_information` | GENIE patient file, local patient data |
| 2 | `cancer_diagnosis`, `imaging`, `clinical_visits`, `surgical_procedures`, `laboratory_testing`, `hospitalizations`, `radiation_treatment`, `comorbidities`, `family_history`, `clinical_trial_history` | Phase 1 |
| 3 | `drug_exposure` (uses diagnosis for regimen context), `tumor_sample_information` (uses GENIE sample file) | Phase 2, GENIE sample file |

Within each table, work through the dictionary in order and classify each field as one of:

- **Pass-through.** Value already matches the GDM code or format.
- **Lookup.** Source value maps to a GDM code through a fixed table (section 6).
- **Derived.** Computed from other fields (all `calc` fields; also flags such as
  `proc_neoadjuvant_yn`, which requires comparing a procedure date to drug start dates).
- **Curated.** No structured source; assigned to the curation team.
- **Not populated.** Rare or unavailable data. Leave null and document why.

Keep this classification in a mapping spreadsheet. It becomes your validation plan and your
data-quality report.

---

## 6. Map vocabularies

### The code is not always the standard code

REDCap stores the *code* half of each `code, label` pair. For most fields the code is a small
integer with a fixed meaning, and for `trt_drug` the code is the NCI Thesaurus concept code
(`C1234`). But for two of the most important fields the code is just the position in the
dropdown, and the standard code lives in the label:

| Field | Stored code | Label | What you probably have |
|---|---|---|---|
| `dx_primary_site` | `0`, `1`, `2`, … | `C00.0 External upper lip`, … | ICD-O-3 topography `C50.9` |
| `dx_morphology` | `1`, `2`, `3`, … | `8000/0, Neoplasm benign`, … | ICD-O-3 morphology `8500/3` |

To map, parse the choice list from the CSV, extract the ICD-O-3 code from the start of each
label, and build a lookup from ICD-O-3 code to REDCap code. Do not assume the numeric code
has any external meaning.

### Common lookup patterns

**NAACCR TNM to AJCC.** Registry T/N/M items carry a `c`/`p` prefix and are upper-cased.
Strip the prefix and restore case: `P1C` becomes `T1c`, `PTIS` becomes `Tis`, `CX` becomes `TX`.
Stage groups use Roman numerals (`IIIA`), not registry abbreviations.

**Yes/No fields** are `1`/`0`. Source values of "Unknown" become null unless the field has an
explicit unknown code (many dropdowns use `9` or `99` for "Not stated / Unknown").

**Checkboxes** (multi-select) become one 0/1 column per option. `imaging_body_location` with
options `1..10` exports as `imaging_body_location___1` … `imaging_body_location___10`.
A source value of "Chest, Abdomen" sets `___4 = 1` and `___5 = 1`.

**"Other" values.** When a coded list has an `Other` code, the accompanying `*_other` text
field carries the verbatim source value. Populate both.

**Drugs.** `trt_drug` uses NCI Thesaurus antineoplastic agent codes (6,962 values in
v1.0.1). Map from RxNorm or local formulary via NCIt; strip salt forms and parenthetical
synonyms before matching. Anything that will not map goes to `trt_drug_other`.

**Institutions.** Fields such as `dx_institution`, `visit_institution` and
`imaging_institution` are `1` = your institution, `2` = external.

### Where to look when a code is ambiguous

The [Curation Directives](../GDM_v1.0.1/GDM_v1.0.1_CurationDirectives.pdf) have a page per
variable with the definition, acceptable source documents and coding instructions. Field
notes in the dictionary cite the NAACCR item number (`[NAACCR #400]`) when one applies.

---

## 7. Apply branching logic, PHI rules and exclusions

**Branching logic is a nullability rule.** The "Shown when" column in the dictionary gives the
condition under which REDCap displays a field. In your output, a field must be null whenever
its condition is false. `trt_drug` is shown when `[trt_yn] = 1 and [trt_trial_yn] = 0`; a
row for a trial drug therefore has `trt_drug` null and the trial fields populated.

**Never share fields flagged PHI.** These are the `Identifier? = y` fields in the CSV: all
`*_date` calendar dates, `patient_mrn`, `patient_study_id`, `birth_date`, `zipcode_full`,
accession and requisition numbers, curator names and free-text curation notes. Keep them
in staging; drop them from anything that leaves the site.

**Exclude curation workflow fields.** `qa_*` fields (curation timestamps, reviewer notes,
error classification) and the `patient_curation_eligibility` instrument are for curation
management. Leave them out of analytic exports unless your data-sharing agreement asks for
them.

**Required fields.** A field marked `Required` must be non-null whenever it is shown. Required
fields whose branching condition is false are legitimately null.

---

## 8. Validate before you share

A minimal checklist. Automate it; you will run it every release.

**Structure**

- [ ] Every output table has exactly the columns named in the dictionary for that instrument
      (minus PHI and `qa_` fields), including one `___n` column per checkbox option.
- [ ] `cancer_patient_information` has one row per patient and `patient_id_curated` is unique.
- [ ] Every `patient_id_curated` in a child table exists in `cancer_patient_information`.
- [ ] Every `patient_id_curated` matches the GENIE format and appears in your GENIE submission.

**Values**

- [ ] Coded fields contain only codes from the dictionary's choice list.
- [ ] Yes/no fields contain only `1`, `0` or null.
- [ ] `_int` fields are non-negative integers and no `_date` field is present.
- [ ] `death_date_int`, `death_year_curated` are populated only when `dead_curated = 1`.
- [ ] `lastalive_date_int >= ` every other `_int` for the same patient (nothing happens after
      last known alive, except death).
- [ ] Required fields are non-null whenever their branching condition is true.
- [ ] Fields are null whenever their branching condition is false.

**Plausibility**

- [ ] `dx_age_yr` equals `round(dx_date_int / 365.25, 4)`.
- [ ] `trt_end_date_int >= trt_start_date_int` where both are present.
- [ ] Row counts per table per patient are within expected ranges (a patient with 400
      imaging rows is worth a look).

---

## 9. Suffix and prefix cheat sheet

| Pattern | Meaning | Share it? |
|---|---|---|
| `*_int` | Days since birth for the paired `*_date` | Yes |
| `*_date` | Calendar date (PHI) | No |
| `*_curated` | Abstracted by a curator or your ETL from local records | Yes |
| `*_tr`, `*_trhis` | Piped in from the tumor registry (NAACCR items, current and historical) | Yes |
| `*_other` | Free text captured when the coded value is "Other" | Yes (review for PHI) |
| `*___n` | One column per checkbox option | Yes |
| `qa_*` | Curation workflow: timestamps, reviewer notes, error types | No |
| `patient_mrn`, `patient_study_id`, `*_acc_num`, `*_requisition_id` | Local identifiers | No |
| `@READONLY` (annotation) | Piped in from Tier1A; do not curate | Yes |

---

## 10. A worked example

The [case study](../etl-plan.html) in this repository maps the public GENIE BPC breast cancer
release (`GENIE BPC BrCa v1.0-public`) into GDM tables field by field, including the
vocabulary lookups it used and the order it ran the tables in. It was produced by one
implementer on one platform. Treat it as an illustration of the steps in this guide, not as
the reference implementation, and note that the source there is a curated GENIE release
rather than raw institutional systems, so several fields were pass-through that will be
lookups or curation for you.

---

## Frequently asked questions

**Do I have to use REDCap?**
No. REDCap is how GENIE's curation teams capture the data and why the schema is expressed as
a REDCap dictionary. Any pipeline that produces tables matching the dictionary is a valid
implementation.

**Can I add fields?**
Add them as separate columns or tables, never by re-purposing a GDM field or code. Keep the
GDM columns exactly as specified so pooled analyses work.

**What about dates before birth, or unknown dates?**
Days-from-birth cannot represent an event before birth, and there is no partial-date
convention in v1.0.1. Leave the `_int` null and, where the instrument offers one, use the
associated "date unknown" or "not documented" code.

**Which layer does a field belong to?**
If the dictionary flags it `read-only / piped in`, it comes from your GENIE submission
(Tier1A). Everything else is extended GDM.

**The PDF, the CSV and the specification disagree. Which wins?**
The CSV is the schema of record for names, types, codes and branching logic. The PDF
governs how a curator decides a value. `SPECIFICATION.md` is explanatory. Report the
discrepancy as an issue so the next release fixes it.
