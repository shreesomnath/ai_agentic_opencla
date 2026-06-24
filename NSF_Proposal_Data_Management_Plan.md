# NSF Proposal: Data Management and Sharing Plan

**Project Title:** Agentic AI for Autonomous Life Cycle Assessment and Sustainability Analytics  
**Funding Program:** Engineering Environmental Resiliency (EER)  

---

## 1. Types of Data to be Produced
The project will generate the following types of data and digital artifacts:
1. **Software Code:** The core Python codebase for the Agentic LCA framework, including the LCI-Agent, LCA-Exe Agent, and SAA-Agent, as well as scripts interfacing with openLCA (`olca-ipc`).
2. **Ontology Mapping Files:** Semantic mapping files, JSON schemas, and lookup dictionaries aligning industry process terms with standard LCA databases (e.g., ecoinvent 3.8 cutoff).
3. **LCA Models & Case Study Data:** Product systems, inventory files (JSON-LD format), and LCIA results generated during validation tests (silicon production and e-waste recycling).
4. **Research Publications & Documentation:** Manuscripts, presentations, and comprehensive user guides for deploying the Agentic LCA tool.

## 2. Standards for Data and Metadata Format
To ensure interoperability, transparency, and reproducibility, all data will adhere to established community standards:
- **LCA Data:** Exported models and inventory data will use the **JSON-LD** and **ILCD (International Reference Life Cycle Data System)** formats, which are fully supported by OpenLCA.
- **Ontologies:** Semantic alignments and mappings will follow RDF/OWL standards.
- **Software Code:** Code will be documented following PEP 8 guidelines for Python, utilizing docstrings and type hinting, and packaged with standard `requirements.txt` or `pyproject.toml` files.
- **Metadata:** Datasets deposited in public repositories will include standardized metadata (e.g., Dublin Core, DCAT) detailing data origin, date of generation, and authors.

## 3. Access and Sharing Policies
We are committed to the principles of open science and FAIR (Findable, Accessible, Interoperable, and Reusable) data:
- **Open Source Software:** All developed software tools will be released under the permissive **Apache License 2.0** or **MIT License** and hosted publicly on GitHub.
- **Data Sharing:** Curated datasets, mapping files, and model templates will be deposited in a public repository (e.g., Zenodo or Figshare) with a digital object identifier (DOI) to facilitate citation.
- **Publications:** Research articles resulting from this project will be submitted to open-access journals or uploaded to preprint servers (e.g., EarthArXiv, arXiv) concurrently with submission.
- **Privacy and IP:** No proprietary industrial data or personally identifiable information (PII) will be collected. All test cases will rely on public databases (ecoinvent) and synthetic, anonymized industry process parameters.

## 4. Reuse and Redistribution Policies
The use of Apache 2.0 / MIT licenses for software code and Creative Commons Attribution (CC-BY 4.0) for datasets will allow other researchers, educators, and industrial practitioners to freely reuse, redistribute, and adapt the research outputs without restrictions, provided appropriate attribution is given.

## 5. Plans for Archiving and Long-Term Preservation
- **Code Preservation:** GitHub repositories will be integrated with Zenodo to automatically mint a permanent DOI and archive snapshots of major software releases.
- **Data Preservation:** Long-term archival of datasets will occur on Zenodo, guaranteeing access for at least 10 years beyond the active funding period.
- **Institutional Repository:** The university library repository will serve as a secondary institutional backup for all publications, thesis work, and project reports.
