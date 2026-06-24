import os
import uuid
import csv
import sys
import json
from flask import Flask, render_template, jsonify, request
from agentic_lca import (
    LcaExecutor, 
    FlowMapper, 
    ThermodynamicVerifier, 
    SensitivityAnalyzer, 
    CostRegistry, 
    MultiObjectiveEvaluator,
    LcaLlmAgent,
    LcaVisualizer,
    LcaCompiler,
    UncertaintyPropagator
)
import olca_schema as o

app = Flask(__name__)

# Ensure static folder exists for saving charts
os.makedirs(os.path.join(app.root_path, 'static'), exist_ok=True)
os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)

# Cache common unit references to avoid querying openLCA on every request
UNIT_MAP = None
def get_cached_units(client):
    global UNIT_MAP
    if UNIT_MAP is not None:
        return UNIT_MAP
        
    processes = list(client.get_descriptors(o.Process))
    sample_proc_desc = next((p for p in processes if "silicone product production" in p.name), None)
    if not sample_proc_desc and processes:
        sample_proc_desc = processes[0]
        
    if sample_proc_desc:
        sample_proc = client.get(o.Process, sample_proc_desc.id)
        UNIT_MAP = {}
        for ex in sample_proc.exchanges:
            if ex.unit:
                UNIT_MAP[ex.unit.name.lower()] = ex.unit
    return UNIT_MAP

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/samples', methods=['GET'])
def get_samples():
    """Returns the pre-configured sample files available."""
    samples = {
        "Silicon Solar Cell (Default)": "sample_bom.csv",
        "Perovskite Tandem Solar Cell": "samples/perovskite_tandem_cell.csv",
        "Wind Turbine Blade": "samples/wind_turbine_blade.csv",
        "Lithium-Ion Battery Pack": "samples/lithium_ion_battery.csv"
    }
    return jsonify(samples)

@app.route('/api/load-sample', methods=['GET'])
def load_sample():
    """Loads a specific BOM file and returns its rows."""
    file_path = request.args.get("file", "sample_bom.csv")
    # Prevent directory traversal
    if ".." in file_path or file_path.startswith("/"):
        return jsonify({"error": "Invalid file path"}), 400
        
    try:
        rows = []
        with open(file_path, mode="r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "flow_name": row["flow_name"],
                    "amount": float(row["amount"]),
                    "unit": row["unit"]
                })
        return jsonify({"success": True, "items": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/optimize', methods=['POST'])
def run_optimization():
    """
    Ingests a BOM (either file or custom list of items), runs sensitivity analysis, 
    performs substitution, saves the comparison chart, and returns metrics.
    """
    data = request.json or {}
    items = data.get("items", [])
    
    # Write items to a temporary BOM file
    temp_bom_path = "temp_bom_web.csv"
    try:
        with open(temp_bom_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["flow_name", "amount", "unit"])
            for item in items:
                writer.writerow([item["flow_name"], item["amount"], item["unit"]])
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to write temporary BOM: {e}"}), 500
        
    # Run optimization logic
    executor = None
    temp_sys_id = None
    temp_proc_id = None
    temp_flow_id = None
    
    try:
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        cost_registry = CostRegistry()
        evaluator = MultiObjectiveEvaluator(executor, verifier, cost_registry)
        analyzer = SensitivityAnalyzer(executor)
        llm_agent = LcaLlmAgent()
        
        # Load units
        unit_map = get_cached_units(executor.client)
        kg_unit = unit_map.get("kg")
        if not kg_unit:
            return jsonify({"success": False, "error": "Kilogram (kg) unit reference not found in database."}), 500
            
        exchanges = []
        total_input_mass = 0.0
        internal_id_counter = 2
        mapping_scores = {}
        
        # 1. Parse temporary BOM
        for item in items:
            flow_name = item["flow_name"]
            amount = float(item["amount"])
            unit_name = item["unit"]
            
            matches = mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
            if not matches:
                continue
            matched_flow, score = matches[0]
            mapping_scores[matched_flow.id] = score
            
            matched_unit = unit_map.get(unit_name.lower(), kg_unit)
            
            exchange = o.Exchange()
            exchange.is_input = True
            exchange.flow = o.Ref(
                ref_type=o.RefType.Flow,
                id=matched_flow.id,
                name=matched_flow.name,
                ref_unit=matched_flow.ref_unit
            )
            exchange.amount = amount
            exchange.unit = o.Ref(ref_type=o.RefType.Unit, id=matched_unit.id, name=matched_unit.name)
            exchange.flow_property = o.Ref(
                ref_type=o.RefType.FlowProperty,
                id="93a60a56-a3c8-11da-a746-0800200b9a66", # Mass
                name="Mass"
            )
            exchange.internal_id = internal_id_counter
            internal_id_counter += 1
            exchanges.append(exchange)
            
            # Mass conservation sum
            if unit_name.lower() == "kg":
                total_input_mass += amount
            elif unit_name.lower() == "g":
                total_input_mass += amount * 1e-3
            elif "water" in flow_name.lower() and unit_name.lower() in ["m3", "cubic meter"]:
                total_input_mass += amount * 1000.0
                
        if not exchanges:
            return jsonify({"success": False, "error": "No BOM flows could be mapped to ecoinvent database."}), 400
            
        # 2. Create finished product flow
        temp_flow_id = str(uuid.uuid4())
        module_flow = o.Flow()
        module_flow.id = temp_flow_id
        module_flow.name = "Web-Synthesized Clean Tech Product"
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
        
        # 3. Create unit process
        temp_proc_id = str(uuid.uuid4())
        process = o.Process()
        process.id = temp_proc_id
        process.name = "Web-Synthesized Product Manufacturing"
        process.process_type = o.ProcessType.UNIT_PROCESS
        
        out_exchange = o.Exchange()
        out_exchange.is_input = False
        out_exchange.flow = o.Ref(ref_type=o.RefType.Flow, id=module_flow.id, name=module_flow.name, ref_unit="kg")
        out_exchange.amount = total_input_mass
        out_exchange.unit = o.Ref(ref_type=o.RefType.Unit, id=kg_unit.id, name=kg_unit.name)
        out_exchange.flow_property = o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
        out_exchange.is_quantitative_reference = True
        out_exchange.internal_id = 1
        
        process.exchanges = [out_exchange] + exchanges
        
        # Mass check
        is_balanced, tvl_report = verifier.verify_mass_balance(process)
        
        # Save process
        executor.client.put(process)
        
        # 4. Compile product system
        sys_ref = executor.client.create_product_system(process)
        if not sys_ref:
            raise RuntimeError("Failed to compile product system.")
        temp_sys_id = sys_ref.id
        
        # Locate ReCiPe
        methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
        if not methods:
            raise ValueError("ReCiPe 2016 Midpoint (H) method not found.")
        method_desc = methods[0]
        
        # 5. Run sensitivities to identify hotspot
        sensitivities = analyzer.analyze_sensitivities(
            process_id=temp_proc_id,
            system_id=temp_sys_id,
            method_id=method_desc.id,
            target_category_query="global warming",
            num_inputs_to_test=5
        )
        
        hotspot_flow_name = None
        highest_elasticity = -1.0
        for name, d in sensitivities.items():
            if d["elasticity"] > highest_elasticity:
                highest_elasticity = d["elasticity"]
                hotspot_flow_name = name
                
        if not hotspot_flow_name:
            raise ValueError("No significant hotspot identified.")
            
        # Find hotspot flow ID
        hotspot_flow_id = None
        for ex in process.exchanges:
            if ex.is_input and ex.flow and ex.flow.name == hotspot_flow_name:
                hotspot_flow_id = ex.flow.id
                break
                
        # 6. Mapped substitute query
        hotspot_lower = hotspot_flow_name.lower()
        if "glass" in hotspot_lower:
            search_query = "glass cullet sorted"
        elif "steel" in hotspot_lower:
            search_query = "scrap steel"
        elif "polyethylene" in hotspot_lower or "plastic" in hotspot_lower:
            search_query = "polyethylene recycled"
        else:
            search_query = f"{hotspot_flow_name.split(',')[0]} recycled"
            
        mapper_results = mapper.search(search_query, top_k=5)
        substitute_flow_desc = None
        for flow_desc, score in mapper_results:
            if flow_desc.id == hotspot_flow_id:
                continue
            if "recycled" in flow_desc.name.lower() or "cullet" in flow_desc.name.lower() or "scrap" in flow_desc.name.lower():
                substitute_flow_desc = flow_desc
                mapping_scores[flow_desc.id] = score
                break
        if not substitute_flow_desc:
            substitute_flow_desc = next((f for f, s in mapper_results if f.id != hotspot_flow_id), None)
            if substitute_flow_desc:
                sub_score = next(s for f, s in mapper_results if f.id == substitute_flow_desc.id)
                mapping_scores[substitute_flow_desc.id] = sub_score
            
        if not substitute_flow_desc:
            raise ValueError(f"No substitute flow found for hotspot '{hotspot_flow_name}'.")
            
        # 7. Evaluate multi-objective Pareto trade-offs
        report = evaluator.evaluate_substitution(
            process_id=temp_proc_id,
            system_id=temp_sys_id,
            method_id=method_desc.id,
            target_flow_id=hotspot_flow_id,
            substitute_flow_desc=substitute_flow_desc,
            mapping_scores=mapping_scores
        )
        
        if report.get("status") != "SUCCESS":
            raise RuntimeError(report.get("message", "Substitution evaluation failed."))
            
        # 8. Generate chart and save in static directory
        chart_filename_dark = "optimization_tradeoffs_dark.png"
        chart_filename_light = "optimization_tradeoffs_light.png"
        chart_path_dark = os.path.join(app.root_path, 'static', chart_filename_dark)
        chart_path_light = os.path.join(app.root_path, 'static', chart_filename_light)
        
        LcaVisualizer.generate_tradeoff_chart(report, chart_path_dark, theme="dark")
        LcaVisualizer.generate_tradeoff_chart(report, chart_path_light, theme="light")
        
        # Save a copy in artifacts too
        LcaVisualizer.generate_tradeoff_chart(
            report, 
            "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_dark.png",
            theme="dark"
        )
        LcaVisualizer.generate_tradeoff_chart(
            report, 
            "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_light.png",
            theme="light"
        )
        
        # 9. LLM justification paragraph
        justification = ""
        if llm_agent.is_ollama_active():
            justification = llm_agent.generate_engineering_justification(report)
            
        # Format exchanges for context list
        exchanges_list = []
        for ex in process.exchanges:
            if ex.is_input and ex.flow:
                exchanges_list.append({
                    "id": ex.flow.id,
                    "name": ex.flow.name,
                    "amount": ex.amount,
                    "unit": ex.unit.name if ex.unit else ""
                })
                
        return jsonify({
            "success": True,
            "report": report,
            "tvl_report": tvl_report,
            "justification": justification,
            "exchanges": exchanges_list,
            "temp_proc_id": temp_proc_id,
            "temp_sys_id": temp_sys_id,
            "method_id": method_desc.id,
            "chart_url_dark": f"/static/{chart_filename_dark}",
            "chart_url_light": f"/static/{chart_filename_light}"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        # Cleanup databases
        if executor:
            if temp_sys_id:
                try: executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys_id))
                except: pass
            if temp_proc_id:
                try: executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=temp_proc_id))
                except: pass
            if temp_flow_id:
                try: executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=temp_flow_id))
                except: pass
        if os.path.exists(temp_bom_path):
            os.remove(temp_bom_path)

@app.route('/api/compile', methods=['POST'])
def compile_hierarchical_bom():
    """
    Ingests a hierarchical JSON BOM, programmatically compiles the processes and product
    system in openLCA, calculates impacts/uncertainty, cleans up, and returns results.
    """
    data = request.json or {}
    bom_data = data.get("bom")
    if not bom_data:
        return jsonify({"success": False, "error": "BOM data is empty"}), 400
        
    executor = None
    flow_ref = None
    proc_ref = None
    sys_ref = None
    
    try:
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        compiler = LcaCompiler(executor, mapper, verifier)
        
        # Compile hierarchical BOM
        flow_ref, proc_ref, sys_ref = compiler.compile_bom(bom_data)
        
        # Locate ReCiPe
        methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
        if not methods:
            raise ValueError("ReCiPe 2016 Midpoint (H) method not found.")
        method_desc = methods[0]
        
        # Fetch the compiled process details to show exchanges
        proc_obj = executor.client.get(o.Process, proc_ref.id)
        exchanges_list = []
        for ex in proc_obj.exchanges:
            if ex.flow:
                exchanges_list.append({
                    "id": ex.flow.id,
                    "name": ex.flow.name,
                    "amount": ex.amount,
                    "unit": ex.unit.name if ex.unit else "",
                    "is_input": ex.is_input
                })
                
        # Run uncertainty propagation on the compiled tree structure!
        print("[Compiler API] Running uncertainty propagation...")
        propagator = UncertaintyPropagator(executor)
        
        # Build mapping scores dict: assign a default high mapping confidence for leaf elements compiled
        mapping_scores = {}
        for ex in exchanges_list:
            mapping_scores[ex["id"]] = 0.85
            
        uncertainty_stats = propagator.propagate(
            process_id=proc_ref.id,
            system_id=sys_ref.id,
            method_id=method_desc.id,
            mapping_scores=mapping_scores,
            num_trials=100
        )
        
        # Parse and format calculation results into the standard KPI visualizer layout
        report_metrics = {}
        for kpi, stat in uncertainty_stats.items():
            report_metrics[kpi] = {
                "baseline": stat["baseline"],
                "baseline_uncertainty": {
                    "stddev": stat["stddev"],
                    "ci_low": stat["ci_low"],
                    "ci_high": stat["ci_high"],
                    "margin_of_error": stat["margin_of_error"]
                },
                "optimized": stat["baseline"],
                "optimized_uncertainty": {
                    "stddev": stat["stddev"],
                    "ci_low": stat["ci_low"],
                    "ci_high": stat["ci_high"],
                    "margin_of_error": stat["margin_of_error"]
                },
                "difference": 0.0,
                "percentage_change": 0.0,
                "unit": stat["unit"]
            }
        
        return jsonify({
            "success": True,
            "flow_id": flow_ref.id,
            "process_id": proc_ref.id,
            "system_id": sys_ref.id,
            "metrics": report_metrics,
            "exchanges": exchanges_list
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        # Cleanup compiled entities from database
        if executor:
            if sys_ref:
                try: executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=sys_ref.id))
                except: pass
            if proc_ref:
                try: executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=proc_ref.id))
                except: pass
            if flow_ref:
                try: executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=flow_ref.id))
                except: pass

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles user queries from the frontend Copilot chat interface.
    Accepts current process exchanges, active report metrics, and user message.
    """
    data = request.json or {}
    message = data.get("message", "").strip()
    exchanges = data.get("exchanges", [])
    report = data.get("report", {})
    temp_proc_id = data.get("temp_proc_id")
    temp_sys_id = data.get("temp_sys_id")
    method_id = data.get("method_id")
    
    if not message:
        return jsonify({"error": "Message is empty"}), 400
        
    try:
        executor = LcaExecutor()
        verifier = ThermodynamicVerifier(tolerance=0.01)
        mapper = FlowMapper(executor)
        cost_registry = CostRegistry()
        evaluator = MultiObjectiveEvaluator(executor, verifier, cost_registry)
        llm_agent = LcaLlmAgent()
        
        # 1. Parse query via LLM
        command = llm_agent.parse_chat_command(message, exchanges, report)
        action = command.get("action", "chat")
        
        if action == "substitute" and temp_proc_id and temp_sys_id and method_id:
            virgin_name = command.get("virgin_flow_name")
            substitute_query = command.get("substitute_search_query")
            
            # Find the target exchange flow ID
            target_flow_id = None
            for ex in exchanges:
                if ex["name"] == virgin_name:
                    target_flow_id = ex["id"]
                    break
                    
            if not target_flow_id:
                return jsonify({
                    "action": "chat",
                    "response": f"I parsed a substitution for '{virgin_name}', but could not find that flow in your active BOM exchanges list."
                })
                
            # Search FlowMapper for substitute
            matches = mapper.search(substitute_query, top_k=5)
            sub_desc = None
            for flow_desc, score in matches:
                if flow_desc.id != target_flow_id:
                    sub_desc = flow_desc
                    break
            if not sub_desc:
                sub_desc = next((f for f, s in matches if f.id != target_flow_id), None)
                
            if not sub_desc:
                return jsonify({
                    "action": "chat",
                    "response": f"I searched the ecoinvent database for '{substitute_query}', but could not find a suitable substitute flow."
                })
                
            # Run substitution calculation dynamically
            # Since the frontend does not save the process permanently in the database, 
            # we need to re-instantiate the process dynamically in a temporary session to calculate.
            # However, for simplicity and speed in the web dashboard chat, we can run this on the server!
            # The backend needs to fetch the details, apply the substitution, run calculation, and return the updated report.
            # To do that, the backend needs to rebuild the process from the exchanges list!
            # Let's perform this rebuild.
            unit_map = get_cached_units(executor.client)
            kg_unit = unit_map.get("kg")
            
            exchanges_objs = []
            total_mass = 0.0
            internal_counter = 2
            
            # Reconstruct exchanges
            for ex in exchanges:
                ex_flow_id = sub_desc.id if ex["id"] == target_flow_id else ex["id"]
                ex_flow_name = sub_desc.name if ex["id"] == target_flow_id else ex["name"]
                
                matched_unit = unit_map.get(ex["unit"].lower(), kg_unit)
                
                new_ex = o.Exchange()
                new_ex.is_input = True
                new_ex.flow = o.Ref(ref_type=o.RefType.Flow, id=ex_flow_id, name=ex_flow_name)
                new_ex.amount = float(ex["amount"])
                new_ex.unit = o.Ref(ref_type=o.RefType.Unit, id=matched_unit.id, name=matched_unit.name)
                new_ex.flow_property = o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
                new_ex.internal_id = internal_counter
                internal_counter += 1
                exchanges_objs.append(new_ex)
                
                # Mass sum
                if ex["unit"].lower() == "kg":
                    total_mass += float(ex["amount"])
                elif ex["unit"].lower() == "g":
                    total_mass += float(ex["amount"]) * 1e-3
                elif "water" in ex["name"].lower() and ex["unit"].lower() in ["m3", "cubic meter"]:
                    total_mass += float(ex["amount"]) * 1000.0
            
            # Rebuild finished flow
            temp_flow_id = str(uuid.uuid4())
            module_flow = o.Flow()
            module_flow.id = temp_flow_id
            module_flow.name = "Web-Rebuild Product"
            module_flow.flow_type = o.FlowType.PRODUCT_FLOW
            module_flow.flow_properties = [
                o.FlowPropertyFactor(
                    is_ref_flow_property=True,
                    conversion_factor=1.0,
                    flow_property=o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
                )
            ]
            executor.client.put(module_flow)
            
            # Rebuild process
            rebuild_proc_id = str(uuid.uuid4())
            process = o.Process()
            process.id = rebuild_proc_id
            process.name = "Web-Rebuild Manufacturing"
            process.process_type = o.ProcessType.UNIT_PROCESS
            
            out_exchange = o.Exchange()
            out_exchange.is_input = False
            out_exchange.flow = o.Ref(ref_type=o.RefType.Flow, id=module_flow.id, name=module_flow.name, ref_unit="kg")
            out_exchange.amount = total_mass
            out_exchange.unit = o.Ref(ref_type=o.RefType.Unit, id=kg_unit.id, name=kg_unit.name)
            out_exchange.flow_property = o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
            out_exchange.is_quantitative_reference = True
            out_exchange.internal_id = 1
            
            process.exchanges = [out_exchange] + exchanges_objs
            
            # Mass balance verifier
            _, tvl_report = verifier.verify_mass_balance(process)
            
            # Put in database
            executor.client.put(process)
            
            # Rebuild product system
            sys_ref = executor.client.create_product_system(process)
            if not sys_ref:
                raise RuntimeError("Failed to compile product system.")
            
            # Reconstruct mapping_scores
            mapping_scores = {}
            for ex in exchanges:
                ex_flow_id = sub_desc.id if ex["id"] == target_flow_id else ex["id"]
                ex_flow_name = sub_desc.name if ex["id"] == target_flow_id else ex["name"]
                
                matches = mapper.search(ex_flow_name, top_k=1)
                score = matches[0][1] if matches else 1.0
                mapping_scores[ex_flow_id] = score

            try:
                # Calculate updated metrics
                sub_report = evaluator.evaluate_substitution(
                    process_id=rebuild_proc_id,
                    system_id=sys_ref.id,
                    method_id=method_id,
                    target_flow_id=target_flow_id,
                    substitute_flow_desc=sub_desc,
                    mapping_scores=mapping_scores
                )
                
                # Save new chart
                chart_filename_dark = "optimization_tradeoffs_dark.png"
                chart_filename_light = "optimization_tradeoffs_light.png"
                chart_path_dark = os.path.join(app.root_path, 'static', chart_filename_dark)
                chart_path_light = os.path.join(app.root_path, 'static', chart_filename_light)
                
                LcaVisualizer.generate_tradeoff_chart(sub_report, chart_path_dark, theme="dark")
                LcaVisualizer.generate_tradeoff_chart(sub_report, chart_path_light, theme="light")
                
                LcaVisualizer.generate_tradeoff_chart(
                    sub_report, 
                    "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_dark.png",
                    theme="dark"
                )
                LcaVisualizer.generate_tradeoff_chart(
                    sub_report, 
                    "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_light.png",
                    theme="light"
                )
                
                # Fetch new LLM justification
                new_just = ""
                if llm_agent.is_ollama_active():
                    new_just = llm_agent.generate_engineering_justification(sub_report)
                    
                # Reconstruct updated exchanges list
                updated_exchanges = []
                for ex_obj in exchanges_objs:
                    updated_exchanges.append({
                        "id": ex_obj.flow.id,
                        "name": ex_obj.flow.name,
                        "amount": ex_obj.amount,
                        "unit": ex_obj.unit.name if ex_obj.unit else ""
                    })
                    
                return jsonify({
                    "action": "substitute",
                    "success": True,
                    "report": sub_report,
                    "tvl_report": tvl_report,
                    "justification": new_just,
                    "exchanges": updated_exchanges,
                    "temp_proc_id": rebuild_proc_id,
                    "temp_sys_id": sys_ref.id,
                    "method_id": method_id,
                    "chart_url_dark": f"/static/{chart_filename_dark}?t={int(time.time())}",
                    "chart_url_light": f"/static/{chart_filename_light}?t={int(time.time())}"
                })
                
            finally:
                # Cleanup rebuild entities
                try: executor.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=sys_ref.id))
                except: pass
                try: executor.client.delete(o.Ref(ref_type=o.RefType.Process, id=rebuild_proc_id))
                except: pass
                try: executor.client.delete(o.Ref(ref_type=o.RefType.Flow, id=temp_flow_id))
                except: pass
                
        else:
            # Just normal chat response
            return jsonify({
                "action": "chat",
                "response": command.get("response", "I could not resolve your query.")
            })
            
    except Exception as e:
        return jsonify({"action": "chat", "response": f"Error processing query: {e}"}), 500

import time
if __name__ == '__main__':
    # Run server on port 5000
    app.run(port=5000, debug=True)
