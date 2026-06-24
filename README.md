# 🌟 Agentic LCA: Autonomous Multi-Agent AI for Lifecycle Assessment

Welcome to **Agentic LCA**, a next-generation scientific AI copilot designed to automate, verify, and optimize Life Cycle Assessments (LCA). 

This platform connects directly to **OpenLCA 2.x** and uses **local offline Large Language Models (LLMs)** (via Ollama) to ingest raw Bills of Materials (BOM), verify thermodynamic mass conservation, dynamically identify environmental hotspots, search circular feedstock substitutes, and evaluate multi-objective Pareto trade-offs.

## 🖥️ Web Dashboard Showcase

Agentic LCA features a custom, premium web dashboard supporting dynamic Bill of Materials editing, real-time Pareto visualizations, and terminal copilot chat reasoning:

| Space Theme (Dark Mode) | Normal Theme (Light Mode) |
| :---: | :---: |
| ![Dark Theme Interface](lca_dashboard_dark.jpg) | ![Light Theme Interface](lca_dashboard_light.jpg) |

---

## 🚀 Key Features

* **🧠 Offline LLM Agentic Copilot**: Talk directly to your LCA model in real-time. Ask questions, get explanations, or command it to run swaps (e.g., *"replace steel with scrap steel"*).
* **📊 Multi-Objective Pareto Optimization**: Evaluates trade-offs across **Climate Change (GWP)**, **Terrestrial Acidification**, **Water Consumption**, and **Financial Material Costs** simultaneously.
* **⚖️ Thermodynamic Verification Layer (TVL)**: Ensures physical realism using stoichiometric and bulk mass conservation checks. It prevents the AI from proposing physically impossible substitutions.
* **🔍 Offline LCI Flow Mapper**: Custom TF-IDF search engine indexes all 65,000+ database flows to map unstructured BOM inputs to structured ecoinvent flows in milliseconds.
* **📦 Apptainer Containerization**: Zero-dependency deployment via a single Singularity Image Format (`.sif`) container file for High-Performance Computing (HPC) and research environments.

---

## 🛠️ Step-by-Step Installation Guide

Follow these steps to set up **Agentic LCA** on your local machine:

### 1. Clone & Set Up Python
Navigate to the directory and install python dependencies using the provided package list:
```bash
git clone https://github.com/shreesomnath/ai_agentic_opencla.git
cd ai_agentic_opencla
pip install -r requirements.txt
```

> [!NOTE]
> For development or to register the global shell command `lca-copilot`, run:
> ```bash
> pip install -e .
> ```

### 2. Configure OpenLCA 2.x
1. Launch **OpenLCA 2.x** and activate your target database (e.g., `ecoinvent` or custom databases).
2. Start the background **IPC Server**:
   * Navigate to `Window` -> `Developer Tools` -> `IPC Server`.
   * Set the port to `8080`.
   * Click **Start** (verify the status is "Running").

### 3. Start Your Local LLM (Ollama)
To enable the automated natural language report justifications and interactive chat copilot:
1. Download and run **Ollama** from [ollama.com](https://ollama.com) (free, open-source).
2. Pull the recommended coding and reasoning model in your terminal:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
3. Keep Ollama active. The pipeline will automatically connect to it at `http://localhost:11434`.

---

## 💻 Running the Tool

You can run the calculations in three modes:

### Mode A: Standard Ingestion & Pareto Optimization
Runs bulk BOM Ingestion, TVL mass checks, sensitivity scans, feedstock optimization, and outputs a trade-offs chart:
```bash
python3 run_pipeline.py
```

### Mode B: Interactive CLI Copilot (Recommended)
Enters an interactive command-line chat session to run feedstock substitutions dynamically:
```bash
python3 run_pipeline.py --chat
```

### Mode C: Graphical Web Dashboard
Launches the premium, theme-toggleable web dashboard with dynamic BOM table editing and visual chat copilot support:
```bash
python3 app.py
```
After starting the server, open your web browser and navigate to: **`http://127.0.0.1:5000/`**

---

## 📋 Selecting Sample BOMs
We have bundled pre-configured case studies representing key clean technologies in the `samples/` directory:

| Technology Case Study | Command to Execute |
| :--- | :--- |
| **Silicon Solar Cell (Default)** | `python3 run_pipeline.py` |
| **Perovskite Tandem Solar Cell** | `python3 run_pipeline.py --bom samples/perovskite_tandem_cell.csv --chat` |
| **Wind Turbine Blade** | `python3 run_pipeline.py --bom samples/wind_turbine_blade.csv --chat` |
| **Lithium-Ion Battery Pack** | `python3 run_pipeline.py --bom samples/lithium_ion_battery.csv --chat` |

---

## 🐳 Reproducibility with Apptainer (Singularity)

For multi-user clusters or zero-install deployments, you can compile and run the system inside an Apptainer container:

```bash
# 1. Build the single SIF container image
apptainer build lca_copilot.sif Apptainer.def

# 2. Run the default optimization pipeline (uses host network to talk to openLCA)
apptainer run --network host lca_copilot.sif

# 3. Launch in interactive chat mode
apptainer run --network host lca_copilot.sif --chat
```

---

## 🎓 Academic Feasibility & Proposal
This software bridge serves as the experimental validation for the NSF CBET Engineering Environmental Resiliency (EER) proposal.
* **LaTeX Source**: [`NSF_Proposal.tex`](NSF_Proposal.tex)
* **Compiled Proposal Document**: [`NSF_Proposal.pdf`](NSF_Proposal.pdf)
