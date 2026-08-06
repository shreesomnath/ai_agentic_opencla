import os
import sys
import platform
import PyInstaller.__main__

def build():
    print("="*80)
    print("    Starting Cross-Platform PyInstaller Build for LCA-Copilot")
    print("="*80)

    # Determine the separator for --add-data based on the OS
    sep = ';' if platform.system() == 'Windows' else ':'
    
    # Calculate base paths to ensure static and templates are bundled
    templates_path = f"templates{sep}templates"
    static_path = f"static{sep}static"
    agentic_path = f"agentic_lca{sep}agentic_lca"

    print(f"Building on {platform.system()} with separator '{sep}'...")
    
    PyInstaller.__main__.run([
        'run_pipeline.py',           # Entry point
        '--name=LCA-Copilot',
        '--onefile',                 # Package into a single executable
        '--console',                 # Keep the console window so users can see Flask startup logs & connect ports
        f'--add-data={templates_path}',
        f'--add-data={static_path}',
        f'--add-data={agentic_path}',
        '--hidden-import=agentic_lca',
        '--hidden-import=agentic_lca.cli',
        '--hidden-import=agentic_lca.coordinator',
        '--hidden-import=agentic_lca.self_healing',
        '--hidden-import=agentic_lca.llm_agent',
        '--hidden-import=agentic_lca.optimization',
        '--hidden-import=flask',
        '--hidden-import=olca_ipc',
        '--hidden-import=olca_schema',
        '--hidden-import=matplotlib',
        '--clean',
        '-y'                         # Overwrite without asking
    ])
    
    print("\n✅ Build completed successfully! Executable can be found in the 'dist' directory.")

if __name__ == '__main__':
    build()
