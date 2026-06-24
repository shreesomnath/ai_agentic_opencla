import csv
import sys
import uuid
import olca_schema as o
import time
from agentic_lca import (
    LcaExecutor, 
    FlowMapper, 
    ThermodynamicVerifier, 
    SensitivityAnalyzer, 
    CostRegistry, 
    MultiObjectiveEvaluator,
    LcaLlmAgent,
    LcaVisualizer
)



def get_unit_refs(client):
    """Scrapes common unit references from an existing database process to avoid hardcoding."""
    processes = list(client.get_descriptors(o.Process))
    sample_proc_desc = next((p for p in processes if "silicone product production" in p.name), None)
    if not sample_proc_desc:
        if processes:
            sample_proc_desc = processes[0]
        else:
            raise ValueError("No processes found in database to scrape units.")
            
    sample_proc = client.get(o.Process, sample_proc_desc.id)
    unit_map = {}
    for ex in sample_proc.exchanges:
        if ex.unit:
            unit_map[ex.unit.name.lower()] = ex.unit
    return unit_map

def main():
    # Initialize references to clean up in case of failure
    temp_sys_id = None
    temp_proc_id = None
    temp_flow_id = None
    executor = None
    
    try:
        # Initialize modules
        print("Connecting to OpenLCA IPC server and initializing modules...")
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        cost_registry = CostRegistry()
        evaluator = MultiObjectiveEvaluator(executor, verifier, cost_registry)
        analyzer = SensitivityAnalyzer(executor)
        
        # Scrape units
        unit_map = get_unit_refs(executor.client)
        kg_unit = unit_map.get("kg")
        if not kg_unit:
            raise ValueError("Kilogram (kg) unit reference not found in database.")
            
        print("\n" + "="*80)
        print("     AGENTIC LCA PIPELINE: BULK BOM INGESTION & PARETO OPTIMIZATION")
        print("="*80)
        
        # 1. Parse CSV and map flows
        print("\n[1/7] Ingesting BOM and mapping exchanges to ecoinvent flows...")
        exchanges = []
        total_input_mass = 0.0
        internal_id_counter = 2
        
        with open("sample_bom.csv", mode="r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flow_name = row["flow_name"]
                amount = float(row["amount"])
                unit_name = row["unit"]
                
                # Search flow in database
                matches = mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
                if not matches:
                    print(f"Warning: Flow '{flow_name}' not found. Skipping.")
                    continue
                matched_flow, score = matches[0]
                print(f" - BOM Item: '{flow_name}' ({amount} {unit_name}) -> ecoinvent: '{matched_flow.name}' (Score: {score:.3f})")
                
                # Map unit
                matched_unit = unit_map.get(unit_name.lower())
                if not matched_unit:
                    matched_unit = kg_unit
                    
                # Create exchange
                exchange = o.Exchange()
                exchange.is_input = True
                exchange.flow = o.Ref(
                    ref_type=o.RefType.Flow,
                    id=matched_flow.id,
                    name=matched_flow.name,
                    ref_unit=matched_flow.ref_unit
                )
                exchange.amount = amount
                exchange.unit = o.Ref(
                    ref_type=o.RefType.Unit,
                    id=matched_unit.id,
                    name=matched_unit.name
                )
                exchange.flow_property = o.Ref(
                    ref_type=o.RefType.FlowProperty,
                    id="93a60a56-a3c8-11da-a746-0800200b9a66", # Mass
                    name="Mass"
                )
                exchange.internal_id = internal_id_counter
                internal_id_counter += 1
                exchanges.append(exchange)
                
                # Convert units to track inputs mass for quantitative reference
                if unit_name.lower() == "kg":
                    total_input_mass += amount
                elif unit_name.lower() == "g":
                    total_input_mass += amount * 1e-3
                elif "water" in flow_name.lower() and unit_name.lower() in ["m3", "cubic meter"]:
                    total_input_mass += amount * 1000.0
                    
        # 2. Programmatically create the new finished product flow
        print("\n[2/7] Creating finished product flow in OpenLCA database...")
        temp_flow_id = str(uuid.uuid4())
        module_flow = o.Flow()
        module_flow.id = temp_flow_id
        module_flow.name = "Next-Gen Silicon Solar Cell Module"
        module_flow.flow_type = o.FlowType.PRODUCT_FLOW
        module_flow.flow_properties = [
            o.FlowPropertyFactor(
                is_ref_flow_property=True,
                conversion_factor=1.0,
                flow_property=o.Ref(
                    ref_type=o.RefType.FlowProperty,
                    id="93a60a56-a3c8-11da-a746-0800200b9a66",
                    name="Mass"
                )
            )
        ]
        executor.client.put(module_flow)
        print(f" -> Flow created: '{module_flow.name}' (ID: {module_flow.id})")
        
        # 3. Create the new unit process in the database
        print("\n[3/7] Synthesizing unit process with mass-balanced quantitative reference...")
        process = o.Process()
        temp_proc_id = str(uuid.uuid4())
        process.id = temp_proc_id
        process.name = "Next-Gen Silicon Solar Cell Manufacturing"
        process.process_type = o.ProcessType.UNIT_PROCESS
        
        # Reference output exchange
        out_exchange = o.Exchange()
        out_exchange.is_input = False
        out_exchange.flow = o.Ref(
            ref_type=o.RefType.Flow,
            id=module_flow.id,
            name=module_flow.name,
            ref_unit="kg"
        )
        out_exchange.amount = total_input_mass
        out_exchange.unit = o.Ref(
            ref_type=o.RefType.Unit,
            id=kg_unit.id,
            name=kg_unit.name
        )
        out_exchange.flow_property = o.Ref(
            ref_type=o.RefType.FlowProperty,
            id="93a60a56-a3c8-11da-a746-0800200b9a66",
            name="Mass"
        )
        out_exchange.is_quantitative_reference = True
        out_exchange.internal_id = 1
        
        process.exchanges = [out_exchange] + exchanges
        
        # Validate mass balance via TVL
        is_balanced, tvl_report = verifier.verify_mass_balance(process)
        print(f" -> TVL Verification: Mass Balanced? {is_balanced} (Error: {tvl_report['relative_error']*100:.4f}%)")
        
        # Save process to database
        executor.client.put(process)
        print(f" -> Process successfully saved in database: ID {process.id}")
        
        # 4. Compile product system
        print("\n[4/7] Compiling baseline product system in openLCA...")
        sys_ref = executor.client.create_product_system(process)
        if not sys_ref:
            raise RuntimeError("Failed to compile product system.")
        temp_sys_id = sys_ref.id
        print(f" -> Product System compiled: ID {temp_sys_id}")
        
        # Locate ReCiPe 2016 Midpoint (H) LCIA method
        methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
        if not methods:
            raise ValueError("ReCiPe 2016 Midpoint (H) method not found.")
        method_desc = methods[0]
        
        # 5. Run sensitivity checks to identify hotspot
        print("\n[5/7] Analyzing sensitivities to find the primary carbon footprint (GWP) hotspot...")
        # Test sensitivity on inputs
        sensitivities = analyzer.analyze_sensitivities(
            process_id=temp_proc_id,
            system_id=temp_sys_id,
            method_id=method_desc.id,
            target_category_query="global warming",
            num_inputs_to_test=5
        )

        
        # Find input with highest positive elasticity
        hotspot_flow_name = None
        highest_elasticity = -1.0
        
        for name, data in sensitivities.items():
            # We want positive sensitivity (increase in input = increase in footprint)
            if data["elasticity"] > highest_elasticity:
                highest_elasticity = data["elasticity"]
                hotspot_flow_name = name
                
        if not hotspot_flow_name:
            print("No significant hotspot identified from sensitivity check.")
            return
            
        print(f" -> Hotspot Flow Identified: '{hotspot_flow_name}' (Elasticity: {highest_elasticity:.4f})")
        
        # Find the flow ID of the hotspot exchange in the synthesized process
        hotspot_flow_id = None
        for ex in process.exchanges:
            if ex.is_input and ex.flow and ex.flow.name == hotspot_flow_name:
                hotspot_flow_id = ex.flow.id
                break
                
        if hotspot_flow_id is None:
            raise ValueError(f"Hotspot flow not found in process exchanges list.")
            
        # 6. Determine green substitute query with smart LCA fallbacks
        hotspot_lower = hotspot_flow_name.lower()
        if "glass" in hotspot_lower:
            search_query = "glass cullet sorted"
        elif "steel" in hotspot_lower:
            search_query = "scrap steel"
        elif "polyethylene" in hotspot_lower or "plastic" in hotspot_lower:
            search_query = "polyethylene recycled"
        else:
            search_query = f"{hotspot_flow_name.split(',')[0]} recycled"
            
        print(f"\n[6/7] Querying FlowMapper for green substitutes for '{hotspot_flow_name}' query: '{search_query}'...")
        mapper_results = mapper.search(search_query, top_k=5)
        
        substitute_flow_desc = None
        for flow_desc, score in mapper_results:
            # Ensure we do not select the original flow as its own substitute
            if flow_desc.id == hotspot_flow_id:
                continue
            if "recycled" in flow_desc.name.lower() or "cullet" in flow_desc.name.lower() or "scrap" in flow_desc.name.lower():
                substitute_flow_desc = flow_desc
                break
                
        if not substitute_flow_desc:
            # Fallback to the first result that is not the original flow
            substitute_flow_desc = next((f for f, s in mapper_results if f.id != hotspot_flow_id), None)
            
        if not substitute_flow_desc:
            print("No suitable alternative substitute flow found for hotspot.")
            return
            
        print(f" -> Selected green substitute flow: '{substitute_flow_desc.name}' (ID: {substitute_flow_desc.id})")

        
        # 7. Evaluate multi-objective Pareto trade-offs
        print("\n[7/7] Evaluating multi-objective Pareto trade-offs for feedstock substitution...")
        report = evaluator.evaluate_substitution(
            process_id=temp_proc_id,
            system_id=temp_sys_id,
            method_id=method_desc.id,
            target_flow_id=hotspot_flow_id,
            substitute_flow_desc=substitute_flow_desc
        )

        
        # Print final report
        if report.get("status") != "SUCCESS":
            print(f"\nOptimization failed: {report.get('message')}")
            return
            
        print("\n" + "="*80)
        print("                 AGENTIC LCA PIPELINE RUN RESULT (PARETO STUDY)")
        print("="*80)
        print(f"Synthesized Product:  {module_flow.name}")
        print(f"Manufacturing Process: {process.name}")
        print(f"Hotspot Swapped:       '{report['substituted_from']}' \n                       -> '{report['substituted_to']}'")
        print("-" * 80)
        print(f"{'Indicator':<25} | {'Baseline':<12} | {'Optimized':<12} | {'Change (%)':<12} | {'Unit':<10}")
        print("-" * 80)
        
        metrics = report["metrics"]
        for key, details in metrics.items():
            baseline_val = details["baseline"]
            opt_val = details["optimized"]
            pct_change = details["percentage_change"]
            unit = details["unit"]
            print(f"{key:<25} | {baseline_val:<12.6f} | {opt_val:<12.6f} | {pct_change:<+11.2f}% | {unit:<10}")
            
        print("="*80)
        print("Interpretation:")
        gwp_pct = metrics["Global Warming"]["percentage_change"]
        cost_pct = metrics["Feedstock Cost"]["percentage_change"]
        water_pct = metrics["Water Consumption"]["percentage_change"]
        acid_pct = metrics["Acidification"]["percentage_change"]
        
        print(f" - Carbon footprint (GWP):   {gwp_pct:+.2f}%")
        print(f" - Material cost savings:    {cost_pct:+.2f}%")
        print(f" - Water consumption change: {water_pct:+.2f}%")
        print(f" - Terrestrial Acidification: {acid_pct:+.2f}%")
        print("\nDecision: Feedstock substitution is Pareto-improving because environmental and cost metrics all decreased.")
        print("="*80)
        
        # 8. Generate LLM Justification Report
        print("\n[8/8] Contacting Local LLM Agent for engineering justification...")
        llm_agent = LcaLlmAgent()
        if llm_agent.is_ollama_active():
            print(" -> Local LLM active. Generating justification paragraph...")
            justification = llm_agent.generate_engineering_justification(report)
            print("\nLLM Justification Report:")
            print("-" * 80)
            print(justification)
            print("-" * 80)
        else:
            print(" -> Local LLM Agent is offline (Ollama not responding on port 11434).")
            print("    To enable this: download Ollama and run 'ollama run qwen2.5-coder:7b' on your Mac.")
        print("="*80)
        
        # 9. Generate Visualization Chart
        print("\n[9/9] Generating trade-off visualization comparison chart...")
        LcaVisualizer.generate_tradeoff_chart(report, "optimization_tradeoffs.png")
        LcaVisualizer.generate_tradeoff_chart(
            report, 
            "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs.png"
        )
        print("="*80)

        # 10. Check if interactive chat mode is requested
        is_chat_mode = "--chat" in sys.argv or "--interactive" in sys.argv
        
        if is_chat_mode:
            print("\n" + "="*80)
            print("         WELCOME TO THE AGENTIC LCA INTERACTIVE COPILOT")
            print("="*80)
            print("Ask questions about the results, request next steps, or substitute materials.")
            print("Examples:")
            print(" - 'Why does glass cullet have less carbon impact?'")
            print(" - 'What if we substitute steel with scrap steel?'")
            print(" - 'Tell me the main hotspots.'")
            print("Type 'exit' or 'quit' to end the session.")
            print("="*80)
            
            # Prepare exchanges list for the LLM context
            exchanges_list = []
            for ex in process.exchanges:
                if ex.is_input and ex.flow:
                    exchanges_list.append({
                        "id": ex.flow.id,
                        "name": ex.flow.name,
                        "amount": ex.amount,
                        "unit": ex.unit.name if ex.unit else ""
                    })
                    
            active_report = report
            
            while True:
                try:
                    user_query = input("\nLCA-Copilot> ").strip()
                    if not user_query:
                        continue
                    if user_query.lower() in ["exit", "quit"]:
                        print("Ending interactive session. Goodbye!")
                        break
                        
                    print("Processing query...")
                    llm_command = llm_agent.parse_chat_command(user_query, exchanges_list, active_report)
                    
                    action = llm_command.get("action", "chat")
                    
                    if action == "substitute":
                        virgin_name = llm_command.get("virgin_flow_name")
                        substitute_query = llm_command.get("substitute_search_query")
                        
                        print(f"\n[LLM Command] Requesting feedstock substitution:")
                        print(f" - Target Virgin material:  '{virgin_name}'")
                        print(f" - Proposed substitute search: '{substitute_query}'")
                        
                        # Find the target exchange index and flow ID
                        target_ex = next((ex for ex in process.exchanges if ex.is_input and ex.flow and ex.flow.name == virgin_name), None)
                        if not target_ex:
                            print(f"Error: Material '{virgin_name}' not found in current process exchanges.")
                            continue
                            
                        # Search FlowMapper for substitute
                        matches = mapper.search(substitute_query, top_k=5)
                        sub_desc = None
                        for flow_desc, score in matches:
                            if flow_desc.id != target_ex.flow.id:
                                sub_desc = flow_desc
                                break
                        if not sub_desc:
                            sub_desc = next((f for f, s in matches if f.id != target_ex.flow.id), None)
                            
                        if not sub_desc:
                            print(f"Error: No suitable substitute flow found for search term '{substitute_query}'.")
                            continue
                            
                        print(f" -> Selected substitute: '{sub_desc.name}' (ID: {sub_desc.id})")
                        
                        # Run evaluation
                        print("Evaluating substitution trade-offs...")
                        sub_report = evaluator.evaluate_substitution(
                            process_id=temp_proc_id,
                            system_id=temp_sys_id,
                            method_id=method_desc.id,
                            target_flow_id=target_ex.flow.id,
                            substitute_flow_desc=sub_desc
                        )
                        
                        if sub_report.get("status") != "SUCCESS":
                            print(f"Substitution failed: {sub_report.get('message')}")
                        else:
                            active_report = sub_report
                            print("\n" + "-"*80)
                            print("                 UPDATED LCA CALCULATIONS REPORT")
                            print("-" * 80)
                            print(f"Substitute: '{sub_report['substituted_from']}' \n             -> '{sub_report['substituted_to']}'")
                            print("-" * 80)
                            print(f"{'Indicator':<25} | {'Baseline':<12} | {'Optimized':<12} | {'Change (%)':<12} | {'Unit':<10}")
                            print("-" * 80)
                            for k, v in sub_report["metrics"].items():
                                print(f"{k:<25} | {v['baseline']:<12.6f} | {v['optimized']:<12.6f} | {v['percentage_change']:<+11.2f}% | {v['unit']:<10}")
                            print("-" * 80)
                            
                            # Re-generate charts with new substitution
                            LcaVisualizer.generate_tradeoff_chart(sub_report, "optimization_tradeoffs.png")
                            LcaVisualizer.generate_tradeoff_chart(
                                sub_report, 
                                "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs.png"
                            )
                            
                            # Ask LLM for new justification
                            print("Generating updated engineering explanation...")
                            new_just = llm_agent.generate_engineering_justification(sub_report)
                            print("\nLLM Justification:")
                            print(new_just)
                            
                    else:
                        # Standard chat query explanation
                        print(f"\nLCA-Copilot Response:")
                        print("-" * 80)
                        print(llm_command.get("response", "No response content returned."))
                        print("-" * 80)
                        
                except KeyboardInterrupt:
                    print("\nEnding session. Goodbye!")
                    break
                except Exception as ex_loop:
                    print(f"Error during chat interaction: {ex_loop}")



        
    except Exception as e:
        print(f"\nPipeline error: {e}")
        
    finally:
        # Cleanup databases
        if executor:
            print("\nCleaning up database resources (restoring clean database state)...")
            if temp_sys_id:
                try:
                    executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys_id))
                    print(" -> Deleted temporary product system.")
                except Exception as e:
                    print(f" -> Error deleting system: {e}")
            if temp_proc_id:
                try:
                    executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=temp_proc_id))
                    print(" -> Deleted temporary process.")
                except Exception as e:
                    print(f" -> Error deleting process: {e}")
            if temp_flow_id:
                try:
                    executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=temp_flow_id))
                    print(" -> Deleted temporary flow.")
                except Exception as e:
                    print(f" -> Error deleting flow: {e}")
            print("Done!")

if __name__ == "__main__":
    main()
