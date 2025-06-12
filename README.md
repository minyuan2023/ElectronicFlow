# ElectronicFlow
Automated Workflow for Electronic Structure Calculations at Catalytic Interfaces, including Bader, Δρ, NELECT, and DOS analysis with parallel handling of multiple adsorbates.

# ElectronicFlow

**ElectronicFlow** is an automated computational workflow tailored for the **electronic structure analysis of catalytic interfaces**. It significantly streamlines the calculation process by automating input file preparation, job submission, and results extraction for key electronic structure properties.

This workflow is built for researchers working in **computational materials science**, **catalysis design**, and **high-throughput screening**, enabling **efficient**, **accurate**, and **scalable** computation of interfacial electronic features.

---

## Key Features

- Automatic generation and editing of DFT input files
- Job submission and real-time monitoring
- Bader charge analysis
- Charge density difference (Δρ) computation
- Total valence electron number (NELECT) estimation
- Density of States (DOS) analysis
- Support for **batch processing** of multiple adsorbates (e.g., *OOH*, *OH*, *O*, etc.)
- Auto-extraction and organized output of results

---

##  Typical Use Cases

- Interfacial electronic analysis of single-site catalysts
- Mechanistic studies of adsorption and charge transfer
- High-throughput evaluation of catalyst candidates
- Automation for machine learning-ready datasets

---

## Requirements

- Python ≥ 3.8  
- VASP (or other DFT engine supported in your scripts)  
- `pymatgen`, `numpy`, `matplotlib`, `ase`, etc.  
- Bader code (`bader` binary)

> Install Python dependencies:
```bash
pip install -r requirements.txt
