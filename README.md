# GENIE Data Model (GDM)

![GENIE Data Model — Core Components](DataModelOverviewImage-1.jpg)

**License: [CC BY-NC-SA](license)** — free to use for non-commercial research with attribution.

The **GENIE Data Model (GDM)** is an open, versioned clinical data standard developed by [AACR Project GENIE](https://www.aacr.org/professionals/research/aacr-project-genie/) to enable harmonized, multi-institutional real-world cancer research. It defines a common structure for cancer patient data across four domains: **Person**, **Diagnosis**, **Treatment**, and **Outcomes**. New versions are released annually on [Synapse](https://www.synapse.org/).

---

## Releases

### [GDM v1.0.1](GDM_v1.0.1/)

| File | Description |
|------|-------------|
| [`GDM_v1.0.1_DataDictionary.csv`](GDM_v1.0.1/GDM_v1.0.1_DataDictionary.csv) | Complete field-level data dictionary |
| [`GDM_v1.0.1_CurationDirectives.pdf`](GDM_v1.0.1/GDM_v1.0.1_CurationDirectives.pdf) | REDCap curation specification with coding rules and derivation logic |
| [`SPECIFICATION.md`](GDM_v1.0.1/SPECIFICATION.md) | Human-readable field specification with types, units, and controlled vocabularies |
| [`GDM_v1.0.1_XML.xml`](GDM_v1.0.1/GDM_v1.0.1_XML.xml) | XML logical model |

---

## Entity Diagrams

The [`diagram/`](diagram/) directory contains SVG logical model diagrams for each GDM entity, including `patient`, `visit`, `condition`, `medication`, `imaging`, `pathology_report`, `genomic`, `observation`, `death`, and more.

---

## License

Released under [CC BY-NC-SA](license). Patient data distributed through AACR Project GENIE is governed separately by the [GENIE Data Use Agreement](https://www.aacr.org/professionals/research/aacr-project-genie/aacr-project-genie-data/).
