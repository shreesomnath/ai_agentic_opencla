---
name: autonomous_lca
description: Automates Life Cycle Assessment (LCA) workflows using Python, olca-ipc, and the openLCA database to calculate environmental impacts.
---

# Autonomous Life Cycle Assessment (LCA) Skill

This skill guides the agent in programmatically interacting with the openLCA software through the `olca-ipc` Python library. It enables autonomous querying, modeling, calculation, and reporting of life cycle impacts from openLCA databases.

## 1. Prerequisites and Setup

To use this skill, ensure that:
1. **openLCA IPC Server is Running**:
   - Open openLCA.
   - Go to `Window` -> `Developer Tools` -> `IPC Server`.
   - Set the port (default: `8080`) and click **Start**.
2. **Python Dependencies are Installed**:
   - `pip install olca-ipc olca-schema`

---

## 2. Core Python IPC Templates

### A. Initializing Connection
Always use the following template to connect to the openLCA IPC server:
```python
import olca_ipc as ipc
import olca_schema as o

client = ipc.Client(port=8080)
```

### B. Searching the Database for Processes or Flows
To run an LCA, you must find the process descriptors first.
```python
# Search for process descriptor by name
processes = client.get_descriptors(o.Process)
solar_processes = [p for p in processes if "solar" in p.name.lower()]

# View fields
for p in solar_processes:
    print(f"Name: {p.name}, ID: {p.id}")
```

### C. Calculating Product System Impacts (LCIA)
To compute impacts, you need a **Product System** and an **LCIA Method**.
```python
# 1. Fetch the target product system
systems = client.get_descriptors(o.ProductSystem)
target_system = next((s for s in systems if "solar" in s.name.lower()), None)

# 2. Fetch the LCIA method
methods = client.get_descriptors(o.ImpactMethod)
target_method = next((m for m in methods if "ReCiPe 2016" in m.name), None)

if target_system and target_method:
    # 3. Define calculation setup
    setup = o.CalculationSetup()
    setup.target = o.Ref(ref_type=o.RefType.ProductSystem, id=target_system.id)
    setup.impact_method = o.Ref(ref_type=o.RefType.ImpactMethod, id=target_method.id)
    setup.amount = 1.0 # 1 unit of product system output
    
    # 4. Calculate
    result = client.calculate(setup)
    
    # 5. Wait/Poll for the async calculation to finish
    while True:
        state = result.get_state()
        if state.is_ready:
            break
        time.sleep(0.5)
        
    # 6. Extract LCIA impact category results
    for val in result.get_total_impacts():
        category = val.impact_category
        unit_str = category.ref_unit if category.ref_unit else ""
        print(f"Impact Category: {category.name}")
        print(f"Value: {val.amount:.6f} {unit_str}")
```

---

## 3. Agentic Workflow for Autonomous LCA

When requested by the user to perform an LCA calculation (e.g., "Find the carbon footprint of a solar module"):
1. **Identify the database in use**: Locate openLCA database files (e.g., `.zolca` files in the workspace).
2. **Launch IPC Connection**: Check if the client can connect to `localhost:8080`.
3. **Query/Inspect**:
   - Write a python script (placed in `scratch/`) to search for the process or product system name specified by the user.
   - Run the script and inspect output.
4. **Create Product System** (if it doesn't exist):
   - If the user specifies a process and no product system is built yet, write a script to auto-generate a product system for that process.
5. **Run Calculation**:
   - Formulate `CalculationSetup` using the selected product system and impact method (such as IPCC 2021 GWP or ReCiPe 2016).
6. **Report Results**:
   - Extract values and format them into a markdown table with indicators, units, values, and a short interpretation of the main contributors.

---

## 4. Troubleshooting and Tips

- **Connection Error**: If `ConnectionRefusedError` occurs, verify that openLCA is open with the active database loaded and the IPC server is active on the matching port.
- **Large Databases**: Querying descriptors (e.g., `client.get_descriptors(o.Flow)`) on large databases like `ecoinvent` can be slow. Apply text filtering or search for `Process` descriptors instead.
- **Reference Types**: Ensure that `o.Ref` is set up with correct `ref_type` (e.g., `RefType.ProductSystem`, `RefType.LciaMethod`, etc.).
