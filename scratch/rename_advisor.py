import os

files = [
    ".github/workflows/build_apptainer.yml",
    ".github/workflows/release.yml",
    "README.md",
    "agentic_lca/cli.py",
    "app.py",
    "static/app.js",
    "setup.py",
    "NSF_Proposal.tex",
    "agentic_lca.egg-info/PKG-INFO"
]

base_dir = "/Users/somnath.luitel/documents/airlab/openlca"

for file in files:
    path = os.path.join(base_dir, file)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 1. Replace Apptainer/Docker references
        content = content.replace("lca_copilot", "agentic_lca")
        
        # 2. Replace textual references
        content = content.replace("Copilot", "Advisor")
        content = content.replace("copilot", "advisor")
        content = content.replace("COPILOT", "ADVISOR")
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {file}")
