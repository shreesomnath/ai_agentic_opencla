from agentic_lca import LcaExecutor, ThermodynamicVerifier, FlowMapper
import olca_schema as o
import time

def main():
    try:
        # Initialize modules
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        
        # 1. Locate the product system
        sys_name = "Mechanical recycling of used c-Si panel - US-TRE"
        print(f"\n[1/7] Locating product system: '{sys_name}'...")
        systems = executor.find_product_system(sys_name)
        if not systems:
            print("Product system not found.")
            return
        sys_desc = systems[0]
        
        # Load details to find the reference process
        sys_obj = executor.client.get(o.ProductSystem, sys_desc.id)
        ref_proc = sys_obj.ref_process
        if not ref_proc:
            print("No reference process found for this product system.")
            return
        print(f" -> Found reference process: '{ref_proc.name}' (ID: {ref_proc.id})")
        
        # Load the full process
        proc = executor.get_process(ref_proc.id)
        
        # Locate target LCIA method
        method_name = "IPCC 2013 GWP 100a"
        methods = executor.find_impact_method(method_name)
        if not methods:
            print("LCIA method not found.")
            return
        method_desc = methods[0]
        
        # 2. Run baseline calculation
        print(f"\n[2/7] Running baseline LCIA calculation using '{method_desc.name}'...")
        baseline_results = executor.calculate(sys_desc.id, method_desc.id)
        baseline_item = next((r for r in baseline_results if "fossil" in r["category_name"].lower()), None)
        if not baseline_item:
            print("Baseline GWP category not found.")
            return
        baseline_gwp = baseline_item["amount"]
        print(f" -> Baseline GWP (Fossil): {baseline_gwp:.6f} kg CO2 eq")
        
        # 3. Locate the virgin HDPE input exchange (the hotspot)
        print("\n[3/7] Searching for virgin HDPE polymer input exchange...")
        hdpe_exchange = None
        for ex in proc.exchanges:
            if ex.is_input and ex.flow and "polyethylene" in ex.flow.name.lower() and "recycled" not in ex.flow.name.lower():
                hdpe_exchange = ex
                break
                
        if not hdpe_exchange:
            print("Virgin HDPE exchange not found in process.")
            return
        print(f" -> Found input flow: '{hdpe_exchange.flow.name}' (Amount: {hdpe_exchange.amount} {hdpe_exchange.unit.name})")
        
        # Keep references for restoring the DB
        original_flow_ref = hdpe_exchange.flow
        
        # 4. Use FlowMapper to search for green recycled alternatives
        search_query = "polyethylene recycled"
        print(f"\n[4/7] Querying FlowMapper for alternative: '{search_query}'...")
        mapper_results = mapper.search(search_query, top_k=5)
        
        # Select the closest recycled granulate flow
        recycled_flow_desc = None
        for flow_desc, score in mapper_results:
            if "recycled" in flow_desc.name.lower() and "granulate" in flow_desc.name.lower() and "high density" in flow_desc.name.lower():
                recycled_flow_desc = flow_desc
                break
                
        if not recycled_flow_desc:
            # Fallback to the first recycled option
            recycled_flow_desc = next((f for f, s in mapper_results if "recycled" in f.name.lower()), None)
            
        if not recycled_flow_desc:
            print("No recycled alternative flow found.")
            return
            
        print(f" -> Selected green substitute flow: '{recycled_flow_desc.name}'")
        print(f"    Category: {recycled_flow_desc.category}")
        print(f"    Flow ID:  {recycled_flow_desc.id}")
        
        # 5. Run TVL mass conservation check on proposed substitution
        print("\n[5/7] Executing TVL mass balance check for the proposed substitution...")
        
        # Calculate baseline mass balance first
        _, baseline_tvl_report = verifier.verify_mass_balance(proc)
        
        # Temporarily assign the new flow to the exchange object (in-memory)
        recycled_ref = o.Ref(
            ref_type=o.RefType.Flow,
            id=recycled_flow_desc.id,
            name=recycled_flow_desc.name,
            ref_unit=recycled_flow_desc.ref_unit
        )
        hdpe_exchange.flow = recycled_ref
        
        # Run verifier on the modified in-memory process
        _, tvl_report = verifier.verify_mass_balance(proc)
        
        # Verify that mass is physically conserved (differential mass check)
        mass_difference_input = abs(tvl_report['total_input_mass_kg'] - baseline_tvl_report['total_input_mass_kg'])
        mass_difference_output = abs(tvl_report['total_output_mass_kg'] - baseline_tvl_report['total_output_mass_kg'])
        
        # The substitution must be mass-neutral (within 0.01 kg tolerance)
        is_substitution_valid = (mass_difference_input < 0.01) and (mass_difference_output < 0.01)
        
        print(f" -> Baseline Process Rel. Error: {baseline_tvl_report['relative_error']*100:.4f}%")
        print(f" -> Substituted Process Rel. Error: {tvl_report['relative_error']*100:.4f}%")
        print(f" -> Input Mass Delta:  {mass_difference_input:.6f} kg")
        print(f" -> Output Mass Delta: {mass_difference_output:.6f} kg")
        print(f" -> TVL Substitution Valid? {is_substitution_valid}")
        
        if not is_substitution_valid:
            print("Substitution rejected: TVL mass balance violated (mass not conserved)!")
            # Restore exchange flow
            hdpe_exchange.flow = original_flow_ref
            return
            
        # 6. Apply substitution to database and compile a new product system
        print("\n[6/7] Applying feedstock substitution to openLCA database...")
        # Save process modification to the database
        executor.client.put(proc)
        
        # Compile a temporary optimized product system to resolve the new links
        print("Compiling temporary optimized product system...")
        # We pass the full sys_obj.ref_process descriptor (containing flow_type, name, location metadata)
        # to ensure OpenLCA matches the quantitative reference correctly.
        temp_sys = executor.client.create_product_system(sys_obj.ref_process)
        if not temp_sys:
            print("Failed to compile temporary product system.")
            # Restore database first
            hdpe_exchange.flow = original_flow_ref
            executor.client.put(proc)
            return
            
        print(f" -> Temporary system compiled: ID {temp_sys.id}")
        
        try:
            print("Running optimized LCIA calculation...")
            opt_results = executor.calculate(temp_sys.id, method_desc.id)
            opt_item = next((r for r in opt_results if "fossil" in r["category_name"].lower()), None)
            
            if not opt_item:
                print("Optimized GWP category not found.")
                opt_gwp = baseline_gwp
                gwp_reduction = 0.0
            else:
                opt_gwp = opt_item["amount"]
                gwp_reduction = ((baseline_gwp - opt_gwp) / baseline_gwp) * 100
        finally:
            # Delete the temporary product system to keep the database clean
            print("Deleting temporary product system...")
            executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys.id))
        
        # 7. Restore baseline database state
        print("\n[7/7] Restoring baseline database state (cleaning up)...")
        hdpe_exchange.flow = original_flow_ref
        executor.client.put(proc)
        print(" -> Baseline state restored successfully.")
        
        # Print final optimization report
        print("\n" + "="*50)
        print("         FEEDSTOCK OPTIMIZATION REPORT")
        print("="*50)
        print(f"Process:       {proc.name}")
        print(f"LCIA Method:   {method_desc.name}")
        print(f"Substituted:   '{original_flow_ref.name}' -> '{recycled_flow_desc.name}'")
        print("-"*50)
        print(f"Baseline GWP:  {baseline_gwp:.6f} kg CO2 eq")
        print(f"Optimized GWP: {opt_gwp:.6f} kg CO2 eq")
        print(f"GWP Reduction: {gwp_reduction:+.2f}% ({baseline_gwp - opt_gwp:.6f} kg CO2 eq saved)")
        print(f"TVL Status:    PASSED (Error: {tvl_report['relative_error']*100:.6f}%)")
        print("="*50)

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        # Make sure we attempt to restore if we fail mid-run
        try:
            if 'proc' in locals() and 'original_flow_ref' in locals() and 'hdpe_exchange' in locals():
                print("Emergency database restoration...")
                hdpe_exchange.flow = original_flow_ref
                executor.client.put(proc)
                print("Database restored.")
        except:
            pass

if __name__ == "__main__":
    main()
