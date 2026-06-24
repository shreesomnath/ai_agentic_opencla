from agentic_lca import LcaExecutor, ThermodynamicVerifier, FlowMapper, MultiObjectiveEvaluator, CostRegistry
import olca_schema as o

def main():
    try:
        print("Connecting to OpenLCA IPC server and initializing modules...")
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        cost_registry = CostRegistry()
        
        evaluator = MultiObjectiveEvaluator(executor, verifier, cost_registry)
        
        # 1. Locate product system
        sys_name = "Mechanical recycling of used c-Si panel - US-TRE"
        print(f"\n[1/5] Locating product system: '{sys_name}'...")
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
        
        # Load the full process to find the exchange index
        proc = executor.get_process(ref_proc.id)
        
        # Find the target flow for virgin HDPE
        hdpe_flow_id = None
        hdpe_flow_name = None
        for ex in proc.exchanges:
            if ex.is_input and ex.flow and "polyethylene" in ex.flow.name.lower() and "recycled" not in ex.flow.name.lower():
                hdpe_flow_id = ex.flow.id
                hdpe_flow_name = ex.flow.name
                break
                
        if hdpe_flow_id is None:
            print("Virgin HDPE exchange not found in process.")
            return
        print(f" -> Found target flow '{hdpe_flow_name}' (ID: {hdpe_flow_id})")
        
        # 2. Locate the substitute flow
        search_query = "polyethylene recycled"
        print(f"\n[2/5] Searching FlowMapper for green substitute: '{search_query}'...")
        mapper_results = mapper.search(search_query, top_k=5)
        
        recycled_flow_desc = None
        for flow_desc, score in mapper_results:
            if "recycled" in flow_desc.name.lower() and "granulate" in flow_desc.name.lower() and "high density" in flow_desc.name.lower():
                recycled_flow_desc = flow_desc
                break
        if not recycled_flow_desc:
            recycled_flow_desc = next((f for f, s in mapper_results if "recycled" in f.name.lower()), None)
            
        if not recycled_flow_desc:
            print("Recycled alternative flow not found.")
            return
        print(f" -> Selected substitute: '{recycled_flow_desc.name}' (ID: {recycled_flow_desc.id})")
        
        # 3. Locate ReCiPe 2016 Midpoint (H) LCIA method
        method_query = "ReCiPe 2016 Midpoint (H)"
        print(f"\n[3/5] Locating LCIA method: '{method_query}'...")
        methods = executor.find_impact_method(method_query)
        if not methods:
            print("LCIA method not found.")
            return
        method_desc = methods[0]
        print(f" -> Found method: '{method_desc.name}' (ID: {method_desc.id})")
        
        # 4. Evaluate substitution trade-offs
        print("\n[4/5] Running multi-objective trade-off evaluation...")
        report = evaluator.evaluate_substitution(
            process_id=ref_proc.id,
            system_id=sys_desc.id,
            method_id=method_desc.id,
            target_flow_id=hdpe_flow_id,
            substitute_flow_desc=recycled_flow_desc
        )

        
        # 5. Print results report
        if report.get("status") != "SUCCESS":
            print(f"\nEvaluation failed: {report.get('message')}")
            return
            
        print("\n" + "="*70)
        print("          MULTI-OBJECTIVE LCA OPTIMIZATION REPORT (TRADE-OFFS)")
        print("="*70)
        print(f"Process:     {report['process_name']}")
        print(f"Substitute:  '{report['substituted_from']}' \n             -> '{report['substituted_to']}'")
        print("-" * 70)
        print(f"{'Indicator':<25} | {'Baseline':<12} | {'Optimized':<12} | {'Change (%)':<12} | {'Unit':<10}")
        print("-" * 70)
        
        metrics = report["metrics"]
        for key, details in metrics.items():
            baseline_val = details["baseline"]
            opt_val = details["optimized"]
            pct_change = details["percentage_change"]
            unit = details["unit"]
            
            print(f"{key:<25} | {baseline_val:<12.6f} | {opt_val:<12.6f} | {pct_change:<+11.2f}% | {unit:<10}")
            
        print("="*70)
        print("Interpretation:")
        gwp_pct = metrics["Global Warming"]["percentage_change"]
        cost_pct = metrics["Feedstock Cost"]["percentage_change"]
        water_pct = metrics["Water Consumption"]["percentage_change"]
        acid_pct = metrics["Acidification"]["percentage_change"]
        
        print(f" - Carbon footprint (GWP):   {gwp_pct:+.2f}%")
        print(f" - Material cost savings:    {cost_pct:+.2f}%")
        print(f" - Water consumption change: {water_pct:+.2f}%")
        print(f" - Terrestrial Acidification: {acid_pct:+.2f}%")
        print("\nDecision: Feedback substitution is Pareto-improving if environmental footprints decrease without economic penalties.")
        print("="*70)

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
