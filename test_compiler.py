from agentic_lca import LcaExecutor, FlowMapper, ThermodynamicVerifier, LcaCompiler
import olca_schema as o

def main():
    try:
        executor = LcaExecutor()
        mapper = FlowMapper(executor)
        verifier = ThermodynamicVerifier()
        compiler = LcaCompiler(executor, mapper, verifier)
        
        # Define hierarchical Wind Turbine Blade BOM
        bom = {
            "name": "Composite Wind Turbine Blade Model",
            "amount": 5000.0,
            "unit": "kg",
            "inputs": [
                {
                    "name": "Fiberglass Composite Structure",
                    "amount": 3000.0,
                    "unit": "kg",
                    "inputs": [
                        {"name": "glass cullet, sorted", "amount": 2500.0, "unit": "kg"},
                        {"name": "polyethylene, high density, granulate", "amount": 500.0, "unit": "kg"}
                    ]
                },
                {
                    "name": "Reinforced Structural Steel Core",
                    "amount": 1500.0,
                    "unit": "kg",
                    "inputs": [
                        {"name": "steel, low-alloyed", "amount": 1400.0, "unit": "kg"},
                        {"name": "tap water", "amount": 100.0, "unit": "kg"}
                    ]
                },
                {
                    "name": "polyethylene, high density, granulate",
                    "amount": 500.0,
                    "unit": "kg"
                }
            ]
        }
        
        print("Compiling hierarchical BOM in openLCA...")
        flow_ref, proc_ref, sys_ref = compiler.compile_bom(bom)
        
        print("\n=== COMPILATION SUCCESS ===")
        print(f"Top-Level Flow Reference:    {flow_ref.name} (ID: {flow_ref.id})")
        print(f"Top-Level Process Reference: {proc_ref.name} (ID: {proc_ref.id})")
        print(f"Generated Product System:   {sys_ref.name} (ID: {sys_ref.id})")
        
        # Run a test calculation on the compiled product system to prove it is fully active
        methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
        if not methods:
            print("Method not found.")
            return
        method_desc = methods[0]
        
        print(f"\nRunning calculation on the compiled product system using '{method_desc.name}'...")
        results = executor.calculate(sys_ref.id, method_desc.id)
        
        print("\n=== IMPACT RESULTS FOR HIERARCHICAL PRODUCT SYSTEM ===")
        for r in results[:4]:
            print(f" - {r['category_name']}: {r['amount']:.6f} {r['unit']}")
            
        # Clean up database objects compiled for test
        print("\nCleaning up compiled entities from openLCA...")
        executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=sys_ref.id))
        executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=proc_ref.id))
        executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=flow_ref.id))
        print("Cleanup complete.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
