#!/usr/bin/env python3
"""Generate a browsable Markdown data dictionary from a REDCap data dictionary CSV.

Usage:
    python3 scripts/build_data_dictionary.py GDM_v1.0.1/GDM_v1.0.1_DataDictionary.csv \
        GDM_v1.0.1/GDM_v1.0.1_XML.xml GDM_v1.0.1/DATA_DICTIONARY.md

The CSV is the REDCap "Data Dictionary" export and is the authoritative field list
for a GDM release. The ODM XML export is read only to discover which instruments
repeat (one row per event) versus which are completed once per patient.

Only the Python standard library is used, so the script runs anywhere Python 3.8+
is installed.
"""
from __future__ import annotations

import csv
import html
import re
import sys
from collections import OrderedDict
from pathlib import Path

csv.field_size_limit(sys.maxsize)

# Above this many choices a code list is summarised instead of printed in full.
MAX_INLINE_CHOICES = 25

# Per-form guidance that cannot be derived from the CSV itself.
FORM_META = {
    "patient_curation_eligibility": {
        "grain": "One record per patient (study-specific eligibility screen).",
        "note": "Internal curation workflow only. Not part of the shared GDM output.",
    },
    "cancer_patient_information": {
        "grain": "One row per patient. Root table; every other curated table joins to it on `patient_id_curated`.",
    },
    "family_history": {"grain": "One row per patient."},
    "comorbidities": {"grain": "One row per patient (NCI Comorbidity Index items)."},
    "cancer_diagnosis": {"grain": "One row per cancer diagnosis (index and non-index cancers)."},
    "imaging": {"grain": "One row per radiology report."},
    "clinical_visits": {"grain": "One row per oncology clinic visit / medical oncologist note."},
    "surgical_procedures": {
        "grain": "One row per pathology report (surgical procedure). Also carries site-specific "
        "biomarkers such as ER/PR/HER2, INI1 and PD-L1.",
    },
    "drug_exposure": {"grain": "One row per cancer-directed drug exposure (trial or non-trial)."},
    "clinical_trial_history": {"grain": "One row per clinical trial enrollment."},
    "radiation_treatment": {
        "grain": "One row per radiation treatment course (section header says one form per treatment), "
        "although the v1.0.1 instrument is not configured as repeating in REDCap.",
    },
    "tumor_sample_information": {"grain": "One row per NGS-sequenced tumor sample."},
    "hospitalizations": {"grain": "One row per in-patient hospitalization."},
    "laboratory_testing": {
        "grain": "One row per laboratory result, although the v1.0.1 instrument is not configured as repeating in REDCap.",
    },
}

# Well-known external vocabularies referenced by very long code lists.
VOCAB_HINTS = [
    (re.compile(r"ICD-O-3 Topography", re.I), "ICD-O-3 topography (C-codes)"),
    (re.compile(r"ICD-O-3 Morphology", re.I), "ICD-O-3 morphology (histology/behavior)"),
    (re.compile(r"NCI[_ ]Thesaurus|evs\.nci\.nih\.gov", re.I), "NCI Thesaurus (NCIt) codes"),
    (re.compile(r"OncoTree", re.I), "OncoTree"),
    (re.compile(r"LOINC", re.I), "LOINC"),
    (re.compile(r"NAACCR", re.I), "NAACCR"),
]


def strip_html(text: str) -> str:
    """Collapse REDCap rich-text labels to plain text."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def parse_choices(raw: str) -> list[tuple[str, str]]:
    out = []
    for part in (raw or "").split("|"):
        part = part.strip()
        if not part:
            continue
        if "," in part:
            code, label = part.split(",", 1)
            out.append((code.strip(), strip_html(label)))
        else:
            out.append((part, ""))
    return out


def vocab_hint(*texts: str) -> str | None:
    blob = " ".join(texts)
    for pattern, name in VOCAB_HINTS:
        if pattern.search(blob):
            return name
    return None


def repeating_forms(xml_path: Path) -> set[str]:
    if not xml_path or not xml_path.exists():
        return set()
    text = xml_path.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r'RepeatInstrument="([^"]+)"', text))


def form_titles(xml_path: Path) -> dict[str, str]:
    if not xml_path or not xml_path.exists():
        return {}
    text = xml_path.read_text(encoding="utf-8", errors="ignore")
    return dict(re.findall(r'<FormDef OID="Form\.([^"]+)" Name="([^"]+)"', text))


def describe_type(row: dict) -> str:
    ftype = row["Field Type"]
    validation = row["Text Validation Type OR Show Slider Number"]
    if ftype == "text":
        if validation.startswith("date"):
            return f"date ({validation})"
        if validation in ("number", "integer"):
            return validation
        if validation == "autocomplete":
            return "text (autocomplete)"
        return "text"
    if ftype == "calc":
        return "calc (derived)"
    if ftype == "yesno":
        return "yes/no (1/0)"
    if ftype == "checkbox":
        return "checkbox (multi-select)"
    return ftype


def choices_cell(row: dict) -> str:
    ftype = row["Field Type"]
    raw = row["Choices, Calculations, OR Slider Labels"]
    if ftype == "calc":
        return f"Formula: `{md_escape(raw.strip())}`"
    if ftype == "yesno":
        return "`1`=Yes, `0`=No"
    if ftype == "checkbox":
        prefix = "Exports as one column per option (`{var}___<code>`). ".format(
            var=row["Variable / Field Name"]
        )
    else:
        prefix = ""
    choices = parse_choices(raw)
    if not choices:
        return prefix.rstrip() or "—"
    if len(choices) > MAX_INLINE_CHOICES:
        hint = vocab_hint(row["Field Label"], row["Field Note"], raw)
        sample = ", ".join(f"`{c}`={md_escape(l)}" for c, l in choices[:3])
        vocab = f" Vocabulary: {hint}." if hint else ""
        return (
            f"{prefix}{len(choices)} coded values (see CSV for full list).{vocab} "
            f"First entries: {sample}, …"
        )
    return prefix + ", ".join(f"`{c}`={md_escape(l)}" if l else f"`{c}`" for c, l in choices)


def flags(row: dict) -> str:
    out = []
    if row["Required Field?"] == "y":
        out.append("**Required**")
    if row["Identifier?"] == "y":
        out.append("PHI (not shared)")
    ann = row["Field Annotation"]
    if "@READONLY" in ann:
        out.append("read-only / piped in")
    if "@HIDEBUTTON" in ann or "@NOW" in ann:
        out.append("workflow")
    if row["Variable / Field Name"].startswith("qa_"):
        out.append("QA")
    return ", ".join(out) if out else "—"


def build(csv_path: Path, xml_path: Path | None) -> str:
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    repeating = repeating_forms(xml_path) if xml_path else set()
    titles = form_titles(xml_path) if xml_path else {}

    forms: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in rows:
        forms.setdefault(r["Form Name"], []).append(r)

    release = csv_path.stem.replace("_DataDictionary", "")
    lines: list[str] = []
    w = lines.append

    w(f"# {release} — Complete Data Dictionary")
    w("")
    w(
        "> **Generated file.** Built by `scripts/build_data_dictionary.py` from "
        f"[`{csv_path.name}`]({csv_path.name}). Do not edit by hand; edit the REDCap "
        "dictionary and re-run the script."
    )
    w("")
    w(
        f"This document lists every one of the **{len(rows)} fields** across the "
        f"**{len(forms)} instruments (tables)** in the {release} REDCap project. "
        "It is the complete companion to the curated, prose-level "
        "[`SPECIFICATION.md`](SPECIFICATION.md), which describes a subset of tables in more depth."
    )
    w("")
    w("## How to read this document")
    w("")
    w("| Column | Meaning |")
    w("|---|---|")
    w("| **Variable** | Exact column name in a REDCap export or a GDM data file. |")
    w("| **Type** | REDCap field type plus validation. `calc (derived)` fields are computed by REDCap and should be reproduced by your ETL. |")
    w("| **Label** | Human-readable question text, with REDCap formatting removed. |")
    w("| **Allowed values / formula** | Coded value list (`code`=meaning), yes/no encoding, or the REDCap formula. Long standard vocabularies are summarised; the full list is in the CSV. |")
    w("| **Shown when** | REDCap branching logic. A field is only populated when this condition is true, so treat it as a nullability rule. |")
    w("| **Flags** | `Required` = must be populated; `PHI` = a direct identifier or calendar date that is never shared outside the site; `read-only / piped in` = imported from the Tier1A GENIE release rather than curated; `QA` / `workflow` = curation-process fields, not clinical content. |")
    w("")
    w("### Conventions that apply everywhere")
    w("")
    w("- **Patient key.** Every clinical instrument carries `patient_id_curated` (the GENIE patient identifier) as the join key back to `cancer_patient_information`.")
    w("- **Dates.** Calendar dates (`*_date`) are PHI and stay at the site. Each has a paired `*_int` field holding **days elapsed since date of birth**, computed with `datediff([birth_date], [x_date], \"d\")`. Share the `_int` field, never the date.")
    w("- **Checkboxes** export as one 0/1 column per option: `field___1`, `field___2`, ….")
    w("- **`*_other`** fields hold free text captured when the coded list has an `Other` choice.")
    w("- **`*_tr` / `*_trhis`** fields are piped in from the institutional tumor registry (NAACCR items); `*_curated` fields are abstracted by a curator.")
    w("- **`qa_*`** fields track curation start/end times, reviewer notes and error classification. Exclude them from analytic exports.")
    w("")

    w("## Tables at a glance")
    w("")
    w("| Table (instrument) | Rows | Fields | Required | Repeats? |")
    w("|---|---|---:|---:|---|")
    for form, frows in forms.items():
        meta = FORM_META.get(form, {})
        req = sum(r["Required Field?"] == "y" for r in frows)
        rep = "per event" if form in repeating else "once per patient"
        w(
            f"| [`{form}`](#{form.replace('_', '-')}) | {md_escape(meta.get('grain', ''))} | "
            f"{len(frows)} | {req} | {rep} |"
        )
    w("")

    for form, frows in forms.items():
        meta = FORM_META.get(form, {})
        title = titles.get(form, form.replace("_", " ").title())
        w("---")
        w("")
        w(f"## `{form}`")
        w("")
        w(f"**{title}.** {meta.get('grain', '')}")
        if meta.get("note"):
            w("")
            w(f"> {meta['note']}")
        w("")
        w(
            f"{len(frows)} fields · {sum(r['Required Field?'] == 'y' for r in frows)} required · "
            f"{'repeating instrument (one row per event)' if form in repeating else 'completed once per patient'}"
        )
        w("")
        # Section headers become sub-groupings within the table.
        w("| Variable | Type | Label | Allowed values / formula | Shown when | Flags |")
        w("|---|---|---|---|---|---|")
        for r in frows:
            section = strip_html(r["Section Header"])
            if section:
                w(f"| **§ {md_escape(section[:120])}** | | | | | |")
            note = strip_html(r["Field Note"])
            label = strip_html(r["Field Label"])
            label_cell = md_escape(label)
            if note:
                label_cell += f" <br><sub>{md_escape(note[:300])}</sub>"
            branch = r["Branching Logic (Show field only if...)"].strip()
            branch_cell = f"`{md_escape(branch)}`" if branch else "always"
            w(
                f"| `{r['Variable / Field Name']}` | {describe_type(r)} | {label_cell} | "
                f"{choices_cell(r)} | {branch_cell} | {flags(r)} |"
            )
        w("")

    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    csv_path = Path(argv[1])
    xml_path = Path(argv[2]) if len(argv) > 3 else None
    out_path = Path(argv[-1])
    out_path.write_text(build(csv_path, xml_path), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
