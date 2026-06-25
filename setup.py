from setuptools import setup, find_packages

setup(
    name="agentic_lca",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "olca-ipc>=2.0.0a0",
        "olca-schema>=2.0.0",
        "requests>=2.25.0",
        "matplotlib>=3.0.0",
        "numpy>=1.20.0",
        "flask>=2.0.0"
    ],
    entry_points={
        "console_scripts": [
            "lca-copilot=agentic_lca.cli:main"
        ]
    },
    author="Somnath Luitel, Dr. Jani Das, Dr. Manmeet Singh",
    description="Autonomous Agentic LCA Multi-Objective Pareto Optimization Copilot",
    url="https://github.com/shreesomnath/ai_agentic_opencla.git",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
