import os

files = [
    ".github/workflows/release.yml",
    "README.md",
    "agentic_lca/cli.py",
    "build.py",
    "setup.bat",
    "setup.py",
    "setup.sh",
    "100_ml_coke_can_lca_report.md",
    "next_gen_silicon_solar_cell_module_lca_report.md",
    "web_synthesized_product_lca_report.md"
]

base_dir = "/Users/somnath.luitel/documents/airlab/openlca"

for file in files:
    path = os.path.join(base_dir, file)
    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        
        # Replace lowercase and uppercase variants
        content = content.replace("lca-copilot", "agentic-lca")
        content = content.replace("LCA-Copilot", "Agentic-LCA")
        content = content.replace("LCA-COPILOT", "AGENTIC-LCA")
        
        with open(path, "w") as f:
            f.write(content)
        print(f"Updated {file}")
