# Agentic AI for Autonomous LCA & Sustainability Analytics

This workspace is set up to develop and demonstrate **Agentic LCA**, an autonomous Artificial Intelligence framework designed to automate Life Cycle Assessment (LCA) workflows using Python and the **OpenLCA 2.x** software.

---

## 1. Project Directory Structure

```text
├── .agents/
│   └── skills/
│       └── autonomous_lca/
│           └── SKILL.md                 # Custom agent skill for OpenLCA 2.x automation
├── agentic_lca/                         # Core Python package for the Agentic LCA prototype
│   ├── __init__.py                      # Package entry point exposing main modules
│   ├── client.py                        # LCA-Exe Agent: wraps OpenLCA IPC connection & solver
│   ├── tvl.py                           # Thermodynamic Verification Layer: mass conservation solver
│   └── uncertainty.py                   # SAA-Agent: Sensitivity analysis and elasticity calculator
├── NSF_Proposal.tex                     # NSF proposal LaTeX source (with vector preliminary charts)
├── NSF_Proposal.pdf                     # Compiled PDF copy of the NSF EER proposal
├── README.md                            # This documentation file
├── test_connection.py                   # Diagnostic script to test OpenLCA IPC connection
├── calculate_gwp.py                     # Demo script running a live LCA calculation loop
├── explore_database.py                  # Utility script to count database descriptors & processes
├── test_tvl.py                          # Integration test for mass-conservation checks (TVL)
├── test_sensitivity.py                  # Integration test for sensitivity & elasticity analysis (SAA)
└── test_mapping.py                      # Integration test for offline flow semantic mapping (LCI)
```

---

## 2. Setting Up the OpenLCA Environment

1. **Open OpenLCA 2.x** and load your database (e.g., `ecoinvent` or custom databases).
2. **Start the IPC Server**:
   * Navigate to `Window` -> `Developer Tools` -> `IPC Server`.
   * Set the port to `8080`.
   * Click **Start** (ensure the server status switches to "Running").

---

## 3. Running the Verification and Testing Scripts

We have installed the OpenLCA 2.x libraries (`olca-ipc` and `olca-schema`) in the local Python environment.

### Connection and Database Inspection
Verify that Python can connect to the running OpenLCA instance and read methods, processes, and descriptor counts:
```bash
python3 test_connection.py
python3 explore_database.py
python3 explore_advanced.py
```

### Live GWP Calculation
Execute a complete Life Cycle Impact Assessment (LCIA) calculation loop:
```bash
python3 calculate_gwp.py
```

### LCI-Agent Flow Semantic Mapping
Run the local, offline TF-IDF vector search engine to map unstructured terms to structured ecoinvent flows (searches 65,000+ flows locally in milliseconds):
```bash
python3 test_mapping.py
```

### Thermodynamic Verification Layer (TVL) mass check
Run bulk mass conservation checks on your active processes (checks inputs/outputs and converts densities like $m^3$ water to $kg$ mass):
```bash
python3 test_tvl.py
```

### Sustainability Analytics Agent (SAA) sensitivity checks
Trigger a finite difference perturbation loop on target process inputs to calculate elasticity metrics relative to Fossil GWP:
```bash
python3 test_sensitivity.py
```

---

## 4. Setting up on Other Devices & LLM Integration

This codebase is packaged to be 100% portable and executable on other devices. Below are the steps for other users or devices to run the pipeline:

### A. Python & Environment Setup
1. Clone this repository to the target device.
2. Install the necessary Python packages using `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

### B. OpenLCA 2.x Configuration
1. Install **OpenLCA 2.x** on the target device.
2. Load an active database (such as ecoinvent).
3. Start the IPC server (`Window` -> `Developer Tools` -> `IPC Server`) on port `8080`.

### C. (Optional) Run Local LLM Reasoning (Ollama)
If they want to enable the automated natural language report justification generator:
1. Download and install **Ollama** from [ollama.com](https://ollama.com).
2. Run the following command in the terminal to pull the recommended coding & reasoning model:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
3. Keep Ollama running in the background. The pipeline will automatically detect the server at `http://localhost:11434` and call it. If Ollama is offline, the pipeline runs normally and falls back gracefully.

### D. Run the Optimization Pipeline
To run the end-to-end bulk BOM ingestion, TVL verification, hotspot sensitivity analysis, and multi-objective Pareto substitution calculations:
```bash
python3 run_pipeline.py
```

---

## 5. Custom Agent Integration
The custom skill at **`.agents/skills/autonomous_lca/SKILL.md`** teaches AI agents (such as Google Antigravity) how to automatically write Python scripts and run them against your databases. This forms the foundation of the proposed **Agentic LCA Execution Agent**.

