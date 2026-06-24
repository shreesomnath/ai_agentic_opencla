import olca_ipc as ipc
import olca_schema as o

client = ipc.Client(8080)
# Let's find one of the compiled nested wind turbine blade processes
processes = list(client.get_descriptors(o.Process))
match = next((p for p in processes if "Test Nested Wind Turbine Blade Model" in p.name), None)

if match:
    print(f"Found process: {match.name} (ID: {match.id})")
    proc = client.get(o.Process, match.id)
    print("Exchanges:")
    for ex in proc.exchanges:
        flow_ref = ex.flow
        print(f" - IsInput: {ex.is_input}")
        print(f"   Flow Ref: ID={flow_ref.id}, Name={flow_ref.name}, RefType={flow_ref.ref_type}")
        if ex.unit:
            print(f"   Unit Ref: ID={ex.unit.id}, Name={ex.unit.name}")
else:
    print("Process not found.")
