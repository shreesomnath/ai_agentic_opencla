# Contributing to Agentic LCA

We welcome contributions from the scientific, LCA, and AI communities! Whether you are fixing bugs, proposing new features, or improving documentation, this guide will help you get started.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shreesomnath/ai_agentic_opencla.git
   cd ai_agentic_opencla
   ```

2. **Set up a Python Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the package in editable mode**:
   ```bash
   pip install -e .
   ```

## Running Unit Tests

Before submitting any code changes, ensure all scientific verification test suites pass successfully. Run the following testing scripts in your terminal:

* **Uncertainty Propagation (Monte Carlo)**:
  ```bash
  python3 test_uncertainty.py
  ```
* **BOM Assembly Linkage & Compiler**:
  ```bash
  python3 test_compiler.py
  ```
* **Thermodynamic Verification Layer (TVL)**:
  ```bash
  python3 test_tvl_elemental.py
  python3 test_tvl_substitution.py
  ```
* **Multi-Objective Optimization**:
  ```bash
  python3 test_multiobjective.py
  ```

## Pull Request Guidelines

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Commit changes** using descriptive commit messages following the Conventional Commits specification (e.g. `feat(tvl): add mass balance checks`).
3. **Format & Document**: Ensure all new functions have docstrings and comments explaining the underlying LCA science or database logic.
4. **Submit a Pull Request** to the `main` branch. Provide a clear explanation of what your changes achieve.
