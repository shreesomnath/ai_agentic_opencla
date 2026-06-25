import os
import uuid
import json
import time
import olca_schema as o
from .client import LcaExecutor
from .tvl import ThermodynamicVerifier
from .mapper import FlowMapper
from .uncertainty import SensitivityAnalyzer
from .multiobjective import CostRegistry
from .optimization import ParetoOptimizer, get_pareto_frontier
from .llm_agent import LcaLlmAgent

class LcaAutonomousCoordinator:
    """
    Coordinates LCI-Agent, LCA-Exe Agent, and SAA-Agent into a fully autonomous
    agentic loop that dynamically redesigns manufacturing processes to meet sustainability goals.
    """
    def __init__(self, executor=None, mapper=None, verifier=None, llm_agent=None, logger=None):
        self.executor = executor if executor else LcaExecutor()
        self.client = self.executor.client
        self.verifier = verifier if verifier else ThermodynamicVerifier(tolerance=0.01)
        self.mapper = mapper if mapper else FlowMapper(self.executor)
        self.cost_registry = CostRegistry()
        self.optimizer = ParetoOptimizer(self.executor, self.mapper, self.verifier, self.cost_registry)
        self.llm_agent = llm_agent if llm_agent else LcaLlmAgent()
        self.logger = logger

    def log(self, message):
        print(message)
        if self.logger:
            try:
                self.logger(message)
            except:
                pass

    def run_optimization_goal(self, bom_items, goal_description, commit_to_db=True):
        """
        Executes the autonomous loop:
        1. Ingest & Map BOM
        2. Mass Balance check (TVL)
        3. Compile baseline Process & Product System
        4. Run baseline calculations
        5. Hotspot analysis (Sensitivity)
        6. Pareto Blending Optimization
        7. LLM selection of the optimal blend matching the goal
        8. (Optional) Commit optimal configuration to database
        9. Generate final verification and report
        """
        print = self.log
        import time
        start_time = time.time()
        if isinstance(bom_items, dict):
            return self._run_hierarchical_optimization_goal(bom_items, goal_description, commit_to_db, start_time)
        print(f"\n[Coordinator] Starting autonomous agent loop for goal: '{goal_description}'")
        
        finished_flow_id = None
        process_id = None
        temp_sys_id = None
        success_exec = False
        
        # 1. Semantic Flow Ingestion & Mapping
        print("\n[Coordinator] Step 1: LCI-Agent - Semantic Ingestion & Mapping...")
        mapped_exchanges = []
        total_input_mass = 0.0
        internal_id_counter = 2
        
        # We need a standard mass unit
        processes = list(self.client.get_descriptors(o.Process))
        kg_unit = None
        for p_desc in processes[:10]:
            try:
                p = self.client.get(o.Process, p_desc.id)
                for ex in p.exchanges:
                    if ex.unit and ex.unit.name.lower() == "kg":
                        kg_unit = ex.unit
                        break
                if kg_unit: break
            except: pass
            
        if not kg_unit:
            # Fallback
            kg_unit = o.Ref(ref_type=o.RefType.Unit, id="125c1281-b681-30eb-8f74-6cb02c2e0b5d", name="kg")
            
        for item in bom_items:
            flow_name = item["flow_name"]
            amount = float(item["amount"])
            unit_name = item["unit"]
            
            print(f" -> Mapping '{flow_name}'...")
            matches = self.mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
            if not matches:
                print(f"    [Warning] Could not map '{flow_name}' to database. Skipping.")
                continue
                
            matched_flow, score = matches[0]
            print(f"    Mapped to: '{matched_flow.name}' (Confidence: {score:.2f})")
            
            exchange = o.Exchange()
            exchange.is_input = True
            exchange.flow = o.Ref(
                ref_type=o.RefType.Flow,
                id=matched_flow.id,
                name=matched_flow.name,
                ref_unit=matched_flow.ref_unit
            )
            exchange.amount = amount
            exchange.amount_formula = f"{amount} * (1 + loss_factor) / process_efficiency"
            exchange.unit = o.Ref(ref_type=o.RefType.Unit, id=kg_unit.id, name=kg_unit.name)
            exchange.flow_property = o.Ref(
                ref_type=o.RefType.FlowProperty,
                id="93a60a56-a3c8-11da-a746-0800200b9a66", # Mass
                name="Mass"
            )
            exchange.internal_id = internal_id_counter
            internal_id_counter += 1
            mapped_exchanges.append(exchange)
            
            # Sum total input mass
            if unit_name.lower() == "kg":
                total_input_mass += amount
            elif unit_name.lower() == "g":
                total_input_mass += amount * 1e-3
                
        if not mapped_exchanges:
            raise ValueError("All input feedstocks failed semantic mapping.")

        # 2. TVL Mass Conservation Verification
        print("\n[Coordinator] Step 2: SAA-Agent - Thermodynamic Mass Verification...")
        # Construct finished flow
        finished_flow_id = str(uuid.uuid4())
        finished_flow = o.Flow()
        finished_flow.id = finished_flow_id
        finished_flow.name = f"Autonomous Synthesized Product - {finished_flow_id[:8]}"
        finished_flow.flow_type = o.FlowType.PRODUCT_FLOW
        finished_flow.flow_properties = [
            o.FlowPropertyFactor(
                is_ref_flow_property=True,
                conversion_factor=1.0,
                flow_property=o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
            )
        ]
        self.client.put(finished_flow)
        
        # Construct unit process
        process_id = str(uuid.uuid4())
        process = o.Process()
        process.id = process_id
        process.name = f"Autonomous Manufacturing - {process_id[:8]}"
        process.process_type = o.ProcessType.UNIT_PROCESS
        
        # Add process parameters
        eff_param = o.Parameter()
        eff_param.name = "process_efficiency"
        eff_param.value = 1.0
        eff_param.is_input_parameter = True
        
        loss_param = o.Parameter()
        loss_param.name = "loss_factor"
        loss_param.value = 0.0
        loss_param.is_input_parameter = True
        
        process.parameters = [eff_param, loss_param]
        
        out_exchange = o.Exchange()
        out_exchange.is_input = False
        out_exchange.flow = o.Ref(ref_type=o.RefType.Flow, id=finished_flow.id, name=finished_flow.name, ref_unit="kg")
        out_exchange.amount = total_input_mass
        out_exchange.unit = o.Ref(ref_type=o.RefType.Unit, id=kg_unit.id, name=kg_unit.name)
        out_exchange.flow_property = o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
        out_exchange.is_quantitative_reference = True
        out_exchange.internal_id = 1
        
        process.exchanges = [out_exchange] + mapped_exchanges
        
        # Verify physical mass conservation
        is_balanced, tvl_report = self.verifier.verify_mass_balance(process)
        print(f" -> TVL Mass Verification Result: {'PASSED' if is_balanced else 'FAILED'}")
        print(f"    Inputs: {tvl_report['total_input_mass_kg']:.3f} kg | Outputs: {tvl_report['total_output_mass_kg']:.3f} kg | Error: {tvl_report['relative_error']*100:.4f}%")
        
        # Save baseline process
        self.client.put(process)
        
        temp_sys_id = None
        try:
            # 3. LCA-Exe Agent: Product System Compiler
            print("\n[Coordinator] Step 3: LCA-Exe Agent - Building Product System...")
            sys_ref = self.client.create_product_system(process)
            if not sys_ref:
                raise RuntimeError("Failed to build product system in openLCA.")
            temp_sys_id = sys_ref.id
            print(f" -> Product system compiled: ID {temp_sys_id}")
            
            # Locate Method
            methods = self.executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
            if not methods:
                raise ValueError("ReCiPe 2016 Midpoint (H) method not found.")
            method_desc = methods[0]
            
            # 4. SAA-Agent: Run baseline LCIA
            print("\n[Coordinator] Step 4: SAA-Agent - Baseline Footprint Assessment...")
            baseline_results = self.executor.calculate(temp_sys_id, method_desc.id)
            
            # Find Global Warming category
            gwp_item = next((r for r in baseline_results if "global warming" in r["category_name"].lower()), None)
            baseline_gwp = gwp_item["amount"] if gwp_item else 0.0
            print(f" -> Baseline Carbon Footprint (GWP): {baseline_gwp:.6f} kg CO2 eq")
            
            # Calculate baseline Cost
            baseline_cost = 0.0
            for ex in mapped_exchanges:
                baseline_cost += self.cost_registry.get_flow_cost(ex.flow.name, ex.amount, "kg")
            print(f" -> Baseline Feedstock Cost: ${baseline_cost:.2f}")

            # 5. SAA-Agent: Hotspot Analysis (Sensitivity)
            print("\n[Coordinator] Step 5: SAA-Agent - Hotspot Sensitivity Analysis...")
            analyzer = SensitivityAnalyzer(self.executor)
            sensitivities = analyzer.analyze_sensitivities(
                process_id=process.id,
                system_id=temp_sys_id,
                method_id=method_desc.id,
                target_category_query="global warming",
                num_inputs_to_test=5
            )
            
            for name, data in sensitivities.items():
                print(f"  - Feedstock '{name}' GWP elasticity: {data['elasticity']:.4f}")

            # 6. SAA-Agent: Pareto Blending Optimization
            print("\n[Coordinator] Step 6: SAA-Agent - Multi-Objective Pareto Optimization...")
            # Run Pareto search with 500 samples
            frontier = self.optimizer.optimize_process(
                process_id=process.id,
                system_id=temp_sys_id,
                method_id=method_desc.id,
                num_samples=500
            )
            print(f" -> Identified {len(frontier)} Pareto-optimal configurations.")
            
            if not frontier:
                print(" -> [Coordinator] No Pareto configurations found (no substitutes). Goal cannot be optimized.")
                return {"success": False, "reason": "No circular feedstock substitutes identified."}
                
            # 7. Consensus Decision Making (Ollama LLM + TOPSIS MCDA)
            print("\n[Coordinator] Step 7: LCI & SAA Agents Consensus - TOPSIS-Weighted LLM Selection...")
            from .decision import TopsisDecisionEngine
            
            # Simple heuristic mapping from natural language goal to TOPSIS priority weights
            topsis_weights = {"GWP": 0.25, "Acidification": 0.25, "Water": 0.25, "Cost": 0.25}
            goal_lower = goal_description.lower()
            if "carbon" in goal_lower or "gwp" in goal_lower or "emission" in goal_lower or "warming" in goal_lower:
                topsis_weights["GWP"] = 0.55
                topsis_weights["Cost"] = 0.15
            if "cost" in goal_lower or "price" in goal_lower or "cheap" in goal_lower or "economic" in goal_lower:
                topsis_weights["Cost"] = 0.55
                topsis_weights["GWP"] = 0.15
            if "water" in goal_lower or "h2o" in goal_lower:
                topsis_weights["Water"] = 0.55
                topsis_weights["GWP"] = 0.15
                topsis_weights["Cost"] = 0.15
            if "acid" in goal_lower:
                topsis_weights["Acidification"] = 0.55
                topsis_weights["GWP"] = 0.15
                topsis_weights["Cost"] = 0.15
                
            print(f" -> Mapping autonomous goal to TOPSIS weights: {topsis_weights}")
            ranked_frontier = TopsisDecisionEngine.rank_alternatives(frontier, topsis_weights)
            selected_point = self._select_best_point_via_llm(ranked_frontier, goal_description)
            print("\n[Coordinator] Optimal Blend selected by Agent Brain:")
            for flow_name, ratio in selected_point["ratios"].items():
                print(f"  - {flow_name}: {ratio:.2%} recycled alternative")
            print("Predicted Metrics:")
            for metric, val in selected_point["metrics"].items():
                print(f"  - {metric}: {val:.6f}")
                
            # 8. LCA-Exe Agent: Commit Redesigned Process
            if commit_to_db:
                print("\n[Coordinator] Step 8: LCA-Exe Agent - Redesigning Process & Parameters in Database...")
                self._apply_optimal_blend_permanently(process, selected_point["ratios"])
                
                # Apply optimal parameters if present
                if "parameters" in selected_point and process.parameters:
                    params = selected_point["parameters"]
                    print(f" -> Applying optimal parameters: process_efficiency={params.get('process_efficiency', 1.0):.4f}, loss_factor={params.get('loss_factor', 0.0):.4f}")
                    # Update process parameters values in database
                    for param in process.parameters:
                        if param.name == "process_efficiency":
                            param.value = float(params.get("process_efficiency", 1.0))
                        elif param.name == "loss_factor":
                            param.value = float(params.get("loss_factor", 0.0))
                    self.client.put(process)
                print(" -> Redesigned process saved permanently.")
                
                # Re-build product system to commit links
                final_sys_ref = self.client.create_product_system(process)
                print(f" -> Final optimized product system compiled: ID {final_sys_ref.id}")
                
                # Run final validation LCIA
                print("\n[Coordinator] Step 9: Final Validation Assessment...")
                final_results = self.executor.calculate(final_sys_ref.id, method_desc.id)
                final_gwp_item = next((r for r in final_results if "global warming" in r["category_name"].lower()), None)
                final_gwp = final_gwp_item["amount"] if final_gwp_item else 0.0
                
                print("="*60)
                print("       AUTONOMOUS LCA AGENT DIRECTIVE REPORT")
                print("="*60)
                print(f"Goal:              {goal_description}")
                print(f"Status:            COMPLETED (SUCCESS)")
                print(f"Baseline GWP:      {baseline_gwp:.6f} kg CO2 eq")
                print(f"Optimized GWP:     {final_gwp:.6f} kg CO2 eq")
                gwp_change = ((baseline_gwp - final_gwp)/baseline_gwp)*100 if baseline_gwp > 0 else 0.0
                print(f"GWP Reduction:     {gwp_change:+.2f}%")
                
                # Calculate final Cost
                final_cost = selected_point["metrics"]["Cost"]
                print(f"Baseline Cost:     ${baseline_cost:.2f}")
                print(f"Optimized Cost:    ${final_cost:.2f}")
                cost_change = ((final_cost - baseline_cost)/baseline_cost)*100 if baseline_cost > 0 else 0.0
                print(f"Cost Change:       {cost_change:+.2f}%")
                elapsed_sec = time.time() - start_time
                print(f"Processing Time:   {int(elapsed_sec // 60)}m {int(elapsed_sec % 60)}s")
                print("="*60)
                
                success_exec = True
                return {
                    "success": True,
                    "baseline_gwp": baseline_gwp,
                    "optimized_gwp": final_gwp,
                    "baseline_cost": baseline_cost,
                    "optimized_cost": final_cost,
                    "optimal_ratios": selected_point["ratios"]
                }
                
            success_exec = True
            return {
                "success": True,
                "optimal_ratios": selected_point["ratios"],
                "predicted_metrics": selected_point["metrics"]
            }
            
        finally:
            if not commit_to_db or not success_exec:
                if temp_sys_id:
                    try: self.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys_id))
                    except: pass
                if process_id:
                    try: self.client.delete(o.Ref(ref_type=o.RefType.Process, id=process_id))
                    except: pass
                if finished_flow_id:
                    try: self.client.delete(o.Ref(ref_type=o.RefType.Flow, id=finished_flow_id))
                    except: pass
            else:
                if temp_sys_id:
                    try: self.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys_id))
                    except: pass

    def _select_best_point_via_llm(self, frontier, goal_description):
        """
        Uses Ollama local model to read the Pareto frontier list and choose
        the point that best satisfies the natural language engineering goal.
        """
        print = self.log
        if not self.llm_agent.is_ollama_active():
            print(" -> [Coordinator Warning] Ollama offline. Defaulting to first Pareto point.")
            return frontier[0]
            
        # Serialize top candidates for the LLM
        # Limit to top 15 points to fit prompt limits comfortably
        points_serialized = []
        for idx, pt in enumerate(frontier[:15]):
            points_serialized.append({
                "index": idx + 1,
                "ratios": pt["ratios"],
                "metrics": pt["metrics"]
            })
            
        prompt = f"""
You are the master coordinator agent of an Autonomous Lifecycle Assessment (LCA) system.
Your goal is: "{goal_description}"

Here are the Pareto-optimal blend configurations (non-dominated trade-offs) computed by the optimization engine:
{json.dumps(points_serialized, indent=2)}

Task:
Select the single best configuration index (1-based) that closest satisfies the goal. 
For example, if the goal is "minimize carbon under cost $15", pick the index that has GWP minimized while Cost <= 15.
If the goal is "minimize cost and cost alone", choose the point with the absolute lowest Cost.

Respond only with a JSON object in this exact format:
{{"selected_index": index_integer, "reasoning": "brief explanation"}}

Output only the JSON object. Do not add any conversational text before or after.
"""
        payload = {
            "model": self.llm_agent.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            response = requests.post(f"{self.llm_agent.ollama_url}/api/generate", json=payload, timeout=20)
            if response.status_code == 200:
                content = response.json().get("response", "").strip()
                ans = json.loads(content)
                idx = int(ans["selected_index"]) - 1
                if 0 <= idx < len(frontier):
                    print(f" -> LLM Selected index {idx+1}. Reason: {ans.get('reasoning')}")
                    return frontier[idx]
        except Exception as e:
            print(f" -> [Coordinator Warning] LLM selection failed ({e}). Defaulting to first point.")
            
        return frontier[0]

    def _apply_optimal_blend_permanently(self, process, optimal_ratios):
        """
        Takes the selected blend ratios and applies the feedstock substitutions permanently
        in the process exchanges. For a ratio r of feedstock X, it splits the exchange:
        - Virgin feedstock amount = (1 - r) * baseline_amount
        - Recycled substitute feedstock amount = r * baseline_amount
        """
        proc = self.client.get(o.Process, process.id)
        
        # Identify the original input exchanges we optimized
        input_exchanges = [e for e in proc.exchanges if e.is_input and e.flow and e.amount > 0]
        
        new_exchanges = []
        # Quantitative reference exchange (index 0 usually)
        out_ex = next(e for e in proc.exchanges if not e.is_input)
        new_exchanges.append(out_ex)
        
        internal_counter = 2
        
        for ex in input_exchanges:
            flow_name = ex.flow.name
            
            # Check if this feedstock has an optimized blending ratio
            matching_ratio_key = next((k for k in optimal_ratios.keys() if k == flow_name), None)
            
            if matching_ratio_key is None:
                # Retain baseline exchange unchanged
                ex.internal_id = internal_counter
                internal_counter += 1
                new_exchanges.append(ex)
                continue
                
            r = optimal_ratios[matching_ratio_key]
            
            if r == 0.0:
                # Keep 100% virgin
                ex.internal_id = internal_counter
                internal_counter += 1
                new_exchanges.append(ex)
                continue
                
            # Locate substitute
            flow_lower = flow_name.lower()
            if "glass" in flow_lower:
                search_query = "glass cullet sorted"
            elif "steel" in flow_lower:
                search_query = "scrap steel"
            elif "polyethylene" in flow_lower or "plastic" in flow_lower:
                search_query = "polyethylene recycled"
            else:
                search_query = f"{flow_name.split(',')[0]} recycled"
                
            matches = self.mapper.search(search_query, top_k=5)
            sub_desc = None
            for fd, score in matches:
                if fd.id != ex.flow.id:
                    if "recycled" in fd.name.lower() or "cullet" in fd.name.lower() or "scrap" in fd.name.lower():
                        sub_desc = fd
                        break
            if not sub_desc and matches:
                sub_desc = next((f for f, s in matches if f.id != ex.flow.id), None)
                
            if not sub_desc:
                # Fallback: keep virgin exchange
                ex.internal_id = internal_counter
                internal_counter += 1
                new_exchanges.append(ex)
                continue
                
            # Create virgin split exchange
            virgin_amount = (1.0 - r) * ex.amount
            if virgin_amount > 0:
                virgin_ex = o.Exchange()
                virgin_ex.is_input = True
                virgin_ex.flow = ex.flow
                virgin_ex.amount = virgin_amount
                virgin_ex.unit = ex.unit
                virgin_ex.flow_property = ex.flow_property
                virgin_ex.internal_id = internal_counter
                internal_counter += 1
                new_exchanges.append(virgin_ex)
                
            # Create recycled split exchange
            recycled_amount = r * ex.amount
            recycled_ex = o.Exchange()
            recycled_ex.is_input = True
            recycled_ex.flow = o.Ref(
                ref_type=o.RefType.Flow,
                id=sub_desc.id,
                name=sub_desc.name,
                ref_unit=sub_desc.ref_unit
            )
            recycled_ex.amount = recycled_amount
            recycled_ex.unit = ex.unit
            recycled_ex.flow_property = ex.flow_property
            recycled_ex.internal_id = internal_counter
            internal_counter += 1
            new_exchanges.append(recycled_ex)
            
        # Put updated exchanges back in process
        proc.exchanges = new_exchanges
        self.client.put(proc)

    def _run_hierarchical_optimization_goal(self, bom_dict, goal_description, commit_to_db, start_time):
        print = self.log
        print("\n[Coordinator] Step 1: Ingesting & Compiling Hierarchical BOM tree...")
        
        # Instantiate LcaCompiler
        from .compiler import LcaCompiler
        compiler = LcaCompiler(self.executor, self.mapper, self.verifier)
        
        success_exec = False
        root_sys_ref = None
        try:
            # Compile tree
            top_flow_ref, top_proc_ref, root_sys_ref = compiler.compile_bom(bom_dict)
            print(f" -> Hierarchical BOM tree compiled.")
            print(f"    Root Process: '{top_proc_ref.name}' (ID: {top_proc_ref.id})")
            print(f"    Root Product System: '{bom_dict['name']}' (ID: {root_sys_ref.id})")
            
            # Locate ReCiPe
            methods = self.executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
            if not methods:
                raise ValueError("ReCiPe 2016 Midpoint (H) method not found.")
            method_desc = methods[0]
            
            # Baseline calculations
            print("\n[Coordinator] Baseline Footprint Assessment on Root Product System...")
            baseline_results = self.executor.calculate(root_sys_ref.id, method_desc.id)
            
            gwp_item = next((r for r in baseline_results if "global warming" in r["category_name"].lower()), None)
            baseline_gwp = gwp_item["amount"] if gwp_item else 0.0
            print(f" -> Baseline Carbon Footprint (GWP): {baseline_gwp:.6f} kg CO2 eq")
            
            # Gather all physical leaf feedstock exchanges recursively
            print("\n[Coordinator] Step 2: SAA-Agent - Recursively identifying leaf feedstock exchanges...")
            leaf_items = self._find_leaf_feedstocks_recursive(top_proc_ref.id, assembly_processes=compiler.assembly_processes)
            print(f" -> Identified {len(leaf_items)} unique physical leaf feedstocks in supply chain:")
            for idx, item in enumerate(leaf_items):
                print(f"    {idx+1}. Process '{item['process_id'][:8]}' feedstock: '{item['exchange'].flow.name}' (Amount: {item['exchange'].amount})")
                
            # Calculate baseline cost
            baseline_cost = 0.0
            for item in leaf_items:
                ex = item["exchange"]
                baseline_cost += self.cost_registry.get_flow_cost(ex.flow.name, ex.amount, "kg")
            print(f" -> Baseline Feedstock Cost: ${baseline_cost:.2f}")
            
            # Identify substitutes
            print("\n[Coordinator] Step 3: Searching substitutes for leaf feedstocks...")
            substitutes = {} # flow_id -> sub_descriptor
            for item in leaf_items:
                ex = item["exchange"]
                flow_id = ex.flow.id
                flow_name = ex.flow.name
                if flow_id in substitutes:
                    continue
                    
                flow_lower = flow_name.lower()
                if "glass" in flow_lower:
                    search_query = "glass cullet sorted"
                elif "steel" in flow_lower:
                    search_query = "scrap steel"
                elif "polyethylene" in flow_lower or "plastic" in flow_lower:
                    search_query = "polyethylene recycled"
                else:
                    search_query = f"{flow_name.split(',')[0]} recycled"
                    
                matches = self.mapper.search(search_query, top_k=5)
                sub_desc = None
                for fd, score in matches:
                    if fd.id != flow_id:
                        if "recycled" in fd.name.lower() or "cullet" in fd.name.lower() or "scrap" in fd.name.lower():
                            sub_desc = fd
                            break
                if not sub_desc and matches:
                    sub_desc = next((f for f, s in matches if f.id != flow_id), None)
                    
                if sub_desc:
                    substitutes[flow_id] = sub_desc
                    print(f"  - Found substitute for '{flow_name}': '{sub_desc.name}'")
                else:
                    print(f"  - [Warning] No suitable recycled substitute found for '{flow_name}'.")
                    
            # Step 4: SAA-Agent - Sensitivity Hotspot Analysis on Root system
            print("\n[Coordinator] Step 4: SAA-Agent - Sensitivity Hotspot Analysis on Root system...")
            sensitivities = {}
            for item in leaf_items:
                ex = item["exchange"]
                flow_id = ex.flow.id
                flow_name = ex.flow.name
                if flow_id not in substitutes:
                    continue
                    
                # Perturb by 10%
                proc_obj = self.client.get(o.Process, item["process_id"])
                target_ex = next(e for e in proc_obj.exchanges if e.flow.id == flow_id)
                orig_amount = target_ex.amount
                
                try:
                    target_ex.amount = orig_amount * 1.10
                    self.client.put(proc_obj)
                    
                    pert_results = self.executor.calculate(root_sys_ref.id, method_desc.id)
                    pert_gwp_item = next((r for r in pert_results if "global warming" in r["category_name"].lower()), None)
                    pert_gwp = pert_gwp_item["amount"] if pert_gwp_item else baseline_gwp
                    
                    # Compute elasticity
                    gwp_pct = (pert_gwp - baseline_gwp) / baseline_gwp if baseline_gwp > 0 else 0.0
                    elasticity = gwp_pct / 0.10
                    sensitivities[flow_name] = elasticity
                    print(f"  - Feedstock '{flow_name}' Root GWP elasticity: {elasticity:.4f}")
                except Exception as e:
                    print(f"    [Error] Calculating sensitivity for '{flow_name}': {e}")
                finally:
                    # Restore original process amount
                    target_ex.amount = orig_amount
                    self.client.put(proc_obj)
                    
            # Step 5: SAA-Agent - Linear Sensitivity Surrogate Blending
            print("\n[Coordinator] Step 5: SAA-Agent - Calculating marginal impacts on Root system...")
            delta_impacts = {}
            target_categories = {
                "GWP": ["global warming"],
                "Acidification": ["acidification"],
                "Water": ["water consumption"]
            }
            category_full_names = {}
            for kpi, queries in target_categories.items():
                found = next((item for item in baseline_results if any(q in item["category_name"].lower() for q in queries)), None)
                category_full_names[kpi] = found["category_name"] if found else kpi
                
            for item in leaf_items:
                ex = item["exchange"]
                flow_id = ex.flow.id
                flow_name = ex.flow.name
                if flow_id not in substitutes:
                    continue
                if flow_id in delta_impacts:
                    continue
                    
                sub_desc = substitutes[flow_id]
                
                # Temporary substitute swap in the database
                proc_obj = self.client.get(o.Process, item["process_id"])
                target_ex = next(e for e in proc_obj.exchanges if e.flow.id == flow_id)
                orig_flow_ref = target_ex.flow
                
                substitute_ref = o.Ref(ref_type=o.RefType.Flow, id=sub_desc.id, name=sub_desc.name, ref_unit=sub_desc.ref_unit)
                target_ex.flow = substitute_ref
                self.client.put(proc_obj)
                
                # Compile temporary root product system
                temp_sys = self.client.create_product_system(top_proc_ref)
                
                delta_impacts[flow_id] = {}
                try:
                    opt_results = self.executor.calculate(temp_sys.id, method_desc.id)
                    for kpi, queries in target_categories.items():
                        opt_item = next((r for r in opt_results if r["category_name"] == category_full_names[kpi]), None)
                        opt_val = opt_item["amount"] if opt_item else 0.0
                        
                        baseline_val = next((r["amount"] for r in baseline_results if r["category_name"] == category_full_names[kpi]), 0.0)
                        delta_impacts[flow_id][kpi] = opt_val - baseline_val
                except Exception as e:
                    print(f"    [Error] Calculating marginal impact of substitute '{sub_desc.name}': {e}")
                    for kpi in target_categories.keys():
                        delta_impacts[flow_id][kpi] = 0.0
                finally:
                    # Cleanup temp system
                    try: self.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys.id))
                    except: pass
                    # Restore original flow
                    target_ex.flow = orig_flow_ref
                    self.client.put(proc_obj)
                    
                # Cost delta
                virgin_cost = self.cost_registry.get_flow_cost(flow_name, ex.amount, "kg")
                recycled_cost = self.cost_registry.get_flow_cost(sub_desc.name, ex.amount, "kg")
                delta_impacts[flow_id]["Cost"] = recycled_cost - virgin_cost
                
            # Step 6: Monte Carlo sampling to find Pareto blends
            print("\n[Coordinator] Step 6: SAA-Agent - Run surrogate Monte Carlo sorting...")
            sampled_points = []
            baselines = {
                "GWP": baseline_gwp,
                "Acidification": next((r["amount"] for r in baseline_results if r["category_name"] == category_full_names["Acidification"]), 0.0),
                "Water": next((r["amount"] for r in baseline_results if r["category_name"] == category_full_names["Water"]), 0.0),
                "Cost": baseline_cost
            }
            
            import random
            for _ in range(500):
                ratios = {}
                for flow_id in substitutes.keys():
                    ratios[flow_id] = random.random()
                    
                pt_metrics = {}
                for kpi in baselines.keys():
                    val = baselines[kpi]
                    for flow_id, r in ratios.items():
                        val += r * delta_impacts[flow_id].get(kpi, 0.0)
                    pt_metrics[kpi] = val
                    
                ratios_named = {}
                for flow_id, r in ratios.items():
                    flow_name = next(item["exchange"].flow.name for item in leaf_items if item["exchange"].flow.id == flow_id)
                    ratios_named[flow_name] = r
                    
                sampled_points.append({
                    "ratios": ratios_named,
                    "metrics": pt_metrics
                })
                
            frontier = get_pareto_frontier(sampled_points)
            print(f" -> Sampled 500 points. Identified {len(frontier)} Pareto configurations.")
            
            # Step 7: LLM Selection (with TOPSIS assistance)
            print("\n[Coordinator] Step 7: Consensus - TOPSIS-Weighted LLM Selection...")
            from .decision import TopsisDecisionEngine
            
            topsis_weights = {"GWP": 0.25, "Acidification": 0.25, "Water": 0.25, "Cost": 0.25}
            goal_lower = goal_description.lower()
            if "carbon" in goal_lower or "gwp" in goal_lower or "emission" in goal_lower or "warming" in goal_lower:
                topsis_weights["GWP"] = 0.55
                topsis_weights["Cost"] = 0.15
            if "cost" in goal_lower or "price" in goal_lower or "cheap" in goal_lower or "economic" in goal_lower:
                topsis_weights["Cost"] = 0.55
                topsis_weights["GWP"] = 0.15
            if "water" in goal_lower or "h2o" in goal_lower:
                topsis_weights["Water"] = 0.55
                topsis_weights["GWP"] = 0.15
                topsis_weights["Cost"] = 0.15
            if "acid" in goal_lower:
                topsis_weights["Acidification"] = 0.55
                topsis_weights["GWP"] = 0.15
                topsis_weights["Cost"] = 0.15
                
            print(f" -> Mapping autonomous goal to TOPSIS weights: {topsis_weights}")
            ranked_frontier = TopsisDecisionEngine.rank_alternatives(frontier, topsis_weights)
            selected_point = self._select_best_point_via_llm(ranked_frontier, goal_description)
            print("\n[Coordinator] Optimal Blend selected by Agent Brain:")
            for flow_name, ratio in selected_point["ratios"].items():
                print(f"  - {flow_name}: {ratio:.2%} recycled alternative")
            print("Predicted Metrics:")
            for metric, val in selected_point["metrics"].items():
                print(f"  - {metric}: {val:.6f}")
                
            # Step 8: Commit Process Redesigns Recursively
            if commit_to_db:
                print("\n[Coordinator] Step 8: LCA-Exe Agent - Committing split-exchanges to DB...")
                
                # Group selected ratios by process_id so we update each sub-assembly process once!
                process_updates = {}
                for item in leaf_items:
                    proc_id = item["process_id"]
                    if proc_id not in process_updates:
                        process_updates[proc_id] = {}
                    flow_name = item["exchange"].flow.name
                    if flow_name in selected_point["ratios"]:
                        process_updates[proc_id][flow_name] = selected_point["ratios"][flow_name]
                        
                for proc_id, optimal_ratios in process_updates.items():
                    proc_desc = self.client.get(o.Process, proc_id)
                    self._apply_optimal_blend_permanently(proc_desc, optimal_ratios)
                    
                # Recompile final root product system
                print("Rebuilding final optimized Hierarchical Product System...")
                final_root_sys = self.client.create_product_system(top_proc_ref)
                print(f" -> Compiled final Root System: ID {final_root_sys.id}")
                
                # Step 9: Final validation calculate
                print("\n[Coordinator] Step 9: Final Validation Assessment on Root system...")
                final_results = self.executor.calculate(final_root_sys.id, method_desc.id)
                final_gwp_item = next((r for r in final_results if "global warming" in r["category_name"].lower()), None)
                final_gwp = final_gwp_item["amount"] if final_gwp_item else 0.0
                
                elapsed_sec = time.time() - start_time
                print("="*60)
                print("       AUTONOMOUS LCA AGENT DIRECTIVE REPORT")
                print("="*60)
                print(f"Goal:              {goal_description}")
                print(f"Status:            COMPLETED (SUCCESS)")
                print(f"Baseline GWP:      {baseline_gwp:.6f} kg CO2 eq")
                print(f"Optimized GWP:     {final_gwp:.6f} kg CO2 eq")
                gwp_change = ((baseline_gwp - final_gwp)/baseline_gwp)*100 if baseline_gwp > 0 else 0.0
                print(f"GWP Reduction:     {gwp_change:+.2f}%")
                
                final_cost = selected_point["metrics"]["Cost"]
                print(f"Baseline Cost:     ${baseline_cost:.2f}")
                print(f"Optimized Cost:    ${final_cost:.2f}")
                cost_change = ((final_cost - baseline_cost)/baseline_cost)*100 if baseline_cost > 0 else 0.0
                print(f"Cost Change:       {cost_change:+.2f}%")
                print(f"Processing Time:   {int(elapsed_sec // 60)}m {int(elapsed_sec % 60)}s")
                print("="*60)
                
                result_dict = {
                    "success": True,
                    "baseline_gwp": baseline_gwp,
                    "optimized_gwp": final_gwp,
                    "baseline_cost": baseline_cost,
                    "optimized_cost": final_cost,
                    "optimal_ratios": selected_point["ratios"]
                }
                success_exec = True
                return result_dict
                
            result_dict = {
                "success": True,
                "optimal_ratios": selected_point["ratios"],
                "predicted_metrics": selected_point["metrics"]
            }
            success_exec = True
            return result_dict
            
        finally:
            if not commit_to_db or not success_exec:
                compiler.cleanup()
            elif root_sys_ref:
                try: self.client.delete(root_sys_ref)
                except: pass

    def _find_leaf_feedstocks_recursive(self, process_id, visited=None, assembly_processes=None):
        if visited is None:
            visited = set()
        if process_id in visited:
            return []
        visited.add(process_id)
        
        proc = self.client.get(o.Process, process_id)
        leaf_feedstocks = []
        
        for ex in proc.exchanges:
            if not (ex.is_input and ex.flow and ex.amount > 0):
                continue
                
            upstream_proc = self._find_process_by_output_flow(ex.flow.name, assembly_processes)
            if upstream_proc:
                leaf_feedstocks.extend(self._find_leaf_feedstocks_recursive(upstream_proc.id, visited, assembly_processes))
            else:
                unit_name = (ex.unit.name or "").lower() if ex.unit else ""
                flow_name = (ex.flow.name or "").lower()
                
                if unit_name in ["kg", "g", "t", "ton", "kg(active substance)"]:
                    if not any(term in flow_name for term in ["electricity", "transport", "freight", "lorry", "air", "water", "heat", "steam", "transmission", "distribution"]):
                        if not any(term in flow_name for term in ["recycled", "cullet", "scrap"]):
                            leaf_feedstocks.append({
                                "process_id": process_id,
                                "exchange": ex
                            })
        return leaf_feedstocks

    def _find_process_by_output_flow(self, flow_name, assembly_processes=None):
        if not flow_name:
            return None
        if assembly_processes and flow_name in assembly_processes:
            return assembly_processes[flow_name]
            
        if flow_name.startswith("Custom Assembly -"):
            assembly_name = flow_name[len("Custom Assembly -"):]
            target_proc_name = f"Custom Process - {assembly_name} Manufacturing"
            
            processes = list(self.client.get_descriptors(o.Process))
            match = next((p for p in processes if p.name == target_proc_name), None)
            if match:
                return match
        return None

import requests
