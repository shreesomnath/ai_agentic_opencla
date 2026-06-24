from agentic_lca import LcaExecutor, SensitivityAnalyzer
import olca_schema as o

def main():
    try:
        executor = LcaExecutor()
        print("Finding product system 'Mechanical recycling of used c-Si panel - US-TRE'...")
        systems = executor.find_product_system("Mechanical recycling of used c-Si panel - US-TRE")
        if not systems:
            print("Product system not found.")
            return
            
        sys_desc = systems[0]
        # In openLCA 2.x, we get the product system object to inspect its reference process
        print(f"Retrieving product system details: {sys_desc.name}...")
        sys_obj = executor.client.get(o.ProductSystem, sys_desc.id)
        
        ref_proc = sys_obj.ref_process
        if not ref_proc:
            print("No reference process found for this product system.")
            return
            
        print(f"Reference Process ID: {ref_proc.id} (Name: {ref_proc.name})")
        
        # Find the LCIA method
        methods = executor.find_impact_method("IPCC 2013 GWP 100a")
        if not methods:
            print("Impact method not found.")
            return
        method_desc = methods[0]
        
        # Initialize the SensitivityAnalyzer
        analyzer = SensitivityAnalyzer(executor)
        
        # Run sensitivity analysis for the top 4 input exchanges
        results = analyzer.analyze_sensitivities(
            process_id=ref_proc.id,
            system_id=sys_desc.id,
            method_id=method_desc.id,
            target_category_query="fossil",
            num_inputs_to_test=4
        )
        
        print("\n=== SENSITIVITY ANALYSIS RESULTS (Elasticity to Fossil GWP) ===")
        # Sort by absolute elasticity value
        sorted_results = sorted(results.items(), key=lambda x: abs(x[1]["elasticity"]), reverse=True)
        
        for name, data in sorted_results:
            elasticity = data["elasticity"]
            print(f" - Flow: '{name}'")
            print(f"   Elasticity: {elasticity:.6f}")
            print(f"   Relative Impact Change for +10% input: {data['delta_impact_percent']:+.4f}%")
            print(f"   Baseline amount: {data['baseline_amount']:.4f} {data['unit']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
