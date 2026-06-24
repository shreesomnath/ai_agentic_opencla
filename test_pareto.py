import sys
from agentic_lca import LcaExecutor, FlowMapper, ThermodynamicVerifier, ParetoOptimizer, CostRegistry
import olca_schema as o

def main():
    try:
        print("Connecting to OpenLCA IPC server and initializing modules...")
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        cost_registry = CostRegistry()
        
        optimizer = ParetoOptimizer(executor, mapper, verifier, cost_registry)
        
        # 1. Locate product system
        sys_name = "Mechanical recycling of used c-Si panel - US-TRE"
        print(f"\n[1/4] Locating product system: '{sys_name}'...")
        systems = executor.find_product_system(sys_name)
        if not systems:
            print("Product system not found.")
            return
        sys_desc = systems[0]
        sys_obj = executor.client.get(o.ProductSystem, sys_desc.id)
        ref_proc = sys_obj.ref_process
        if not ref_proc:
            print("Reference process not found.")
            return
        print(f" -> Found process: '{ref_proc.name}' (ID: {ref_proc.id})")
        
        # 2. Locate ReCiPe 2016 Midpoint (H) LCIA method
        method_query = "ReCiPe 2016 Midpoint (H)"
        print(f"\n[2/4] Locating LCIA method: '{method_query}'...")
        methods = executor.find_impact_method(method_query)
        if not methods:
            print("LCIA method not found.")
            return
        method_desc = methods[0]
        print(f" -> Found method: '{method_desc.name}' (ID: {method_desc.id})")
        
        # 3. Run Pareto Optimizer
        print("\n[3/4] Running Pareto Optimizer (Linear surrogate model + Monte Carlo sampling)...")
        frontier = optimizer.optimize_process(
            process_id=ref_proc.id,
            system_id=sys_desc.id,
            method_id=method_desc.id,
            num_samples=500
        )
        
        # 4. Print results
        print("\n[4/4] Optimization Results:")
        print("="*80)
        print(f"Total Pareto-optimal points found: {len(frontier)}")
        print("="*80)
        
        if not frontier:
            print("No Pareto-optimal points found. Check if substitute feedstocks were identified.")
            return
            
        # Display top 5 Pareto-optimal blend configurations
        print(f"Displaying up to 5 representative Pareto points:")
        for idx, pt in enumerate(frontier[:5]):
            print(f"\nPareto Point #{idx+1}:")
            print("  Blend ratios (secondary/recycled feedstock fraction):")
            for flow_name, ratio in pt["ratios"].items():
                print(f"    - {flow_name}: {ratio:.2%} recycled")
            print("  Estimated Metrics:")
            for metric, val in pt["metrics"].items():
                print(f"    - {metric:<15}: {val:.6f}")
        print("="*80)
        
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
