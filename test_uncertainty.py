from agentic_lca import LcaExecutor, UncertaintyPropagator
import olca_schema as o
import json

def main():
    try:
        executor = LcaExecutor()
        print("Finding product system 'Mechanical recycling of used c-Si panel - US-TRE'...")
        systems = executor.find_product_system("Mechanical recycling of used c-Si panel - US-TRE")
        if not systems:
            print("Product system not found.")
            return
            
        sys_desc = systems[0]
        print(f"Retrieving product system details: {sys_desc.name}...")
        sys_obj = executor.client.get(o.ProductSystem, sys_desc.id)
        
        ref_proc = sys_obj.ref_process
        if not ref_proc:
            print("No reference process found for this product system.")
            return
            
        print(f"Reference Process ID: {ref_proc.id} (Name: {ref_proc.name})")
        
        # Find the LCIA method
        methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
        if not methods:
            print("ReCiPe 2016 Midpoint (H) method not found.")
            return
        method_desc = methods[0]
        
        # Initialize UncertaintyPropagator
        propagator = UncertaintyPropagator(executor)
        
        # Define some sample mapping scores (e.g. 0.85 for glass, 0.70 for polyethylene, etc.)
        # We can look up input exchanges to match their IDs
        proc = executor.client.get(o.Process, ref_proc.id)
        mapping_scores = {}
        
        print("\nInput Exchanges:")
        for ex in proc.exchanges:
            if ex.is_input and ex.flow:
                # Assign a mock mapping score representing AI classification confidence
                # Let's say we have 90% confidence for glass, 75% for silicon, etc.
                flow_name_lower = ex.flow.name.lower()
                if "glass" in flow_name_lower:
                    score = 0.90
                elif "silicon" in flow_name_lower:
                    score = 0.75
                elif "water" in flow_name_lower:
                    score = 0.95
                else:
                    score = 0.80
                mapping_scores[ex.flow.id] = score
                print(f" - Flow: '{ex.flow.name}' | Assigned confidence score: {score:.2f}")
                
        # Run uncertainty propagation (Monte Carlo with 100 trials for speed in testing)
        print("\nRunning uncertainty propagation (Monte Carlo, 100 trials)...")
        stats = propagator.propagate(
            process_id=ref_proc.id,
            system_id=sys_desc.id,
            method_id=method_desc.id,
            mapping_scores=mapping_scores,
            num_trials=100
        )
        
        print("\n=== UNCERTAINTY PROPAGATION RESULTS ===")
        print(json.dumps(stats, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
