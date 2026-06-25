import os
import uuid
import csv
import sys
import json
from flask import Flask, render_template, jsonify, request, Response
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
    UncertaintyPropagator,
    ParetoOptimizer,
    LcaAutonomousCoordinator
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

# Connection configurations & global variables
CURRENT_IPC_PORT = 8080
executor = None
mapper = None
CONNECTION_SUCCESS = False
CONNECTION_ERROR = None

def init_ipc_connection(port=8080):
    global executor, mapper, CURRENT_IPC_PORT, CONNECTION_SUCCESS, CONNECTION_ERROR
    CURRENT_IPC_PORT = port
    print(f"Initializing global LcaExecutor and FlowMapper on port {port}...")
    try:
        executor = LcaExecutor(port=port)
        # Test connection by querying a quick descriptor
        executor.client.get_descriptors(o.FlowProperty)
        mapper = FlowMapper(executor)
        CONNECTION_SUCCESS = True
        CONNECTION_ERROR = None
        print(" -> Global IPC Connection established and database indexed successfully!")
        return True
    except Exception as e:
        executor = None
        mapper = None
        CONNECTION_SUCCESS = False
        CONNECTION_ERROR = str(e)
        print(f" -> Global IPC Connection failed: {e}")
        return False

# Initialize connection on startup
init_ipc_connection(8080)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_connection_status():
    """
    Returns current connection status, port, and database statistics.
    """
    global CONNECTION_SUCCESS, CURRENT_IPC_PORT, CONNECTION_ERROR, mapper, executor
    if CONNECTION_SUCCESS and mapper and executor:
        try:
            flows_count = len(mapper.flows)
            processes_count = len(list(executor.client.get_descriptors(o.Process)))
            is_empty_db = (flows_count == 0)
            return jsonify({
                "success": True,
                "connected": True,
                "port": CURRENT_IPC_PORT,
                "flows_count": flows_count,
                "processes_count": processes_count,
                "is_empty_db": is_empty_db
            })
        except Exception as e:
            return jsonify({
                "success": True,
                "connected": False,
                "port": CURRENT_IPC_PORT,
                "error": f"Connected but stats query failed: {e}"
            })
    else:
        return jsonify({
            "success": True,
            "connected": False,
            "port": CURRENT_IPC_PORT,
            "error": CONNECTION_ERROR or "No active connection"
        })

@app.route('/api/process-parameters', methods=['GET'])
def get_process_parameters():
    """
    Given a flow name, searches for the corresponding process in the database,
    and returns its input parameters list.
    """
    global executor, mapper, CONNECTION_SUCCESS
    if not CONNECTION_SUCCESS or not executor or not mapper:
        return jsonify({"success": False, "error": "openLCA is not connected"}), 500
        
    flow_name = request.args.get("flow_name", "").strip()
    if not flow_name:
        return jsonify({"success": False, "error": "flow_name is required"}), 400
        
    try:
        matches = mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
        if not matches:
            return jsonify({"success": True, "parameters": []})
            
        flow_desc, score = matches[0]
        processes = list(executor.client.get_descriptors(o.Process))
        matching_proc_desc = next((p for p in processes if flow_name.lower() in p.name.lower()), None)
        if not matching_proc_desc:
            matching_proc_desc = next((p for p in processes if flow_desc.name.lower() in p.name.lower()), None)
            
        if not matching_proc_desc:
            return jsonify({"success": True, "parameters": []})
            
        proc = executor.client.get(o.Process, matching_proc_desc.id)
        params = []
        if proc.parameters:
            for p in proc.parameters:
                if p.is_input_parameter:
                    params.append({
                        "name": p.name,
                        "value": p.value,
                        "description": p.description or "",
                        "process_id": proc.id,
                        "process_name": proc.name
                    })
        return jsonify({"success": True, "parameters": params})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

@app.route('/api/sync', methods=['POST'])
def sync_database():
    """
    Re-establishes connection to openLCA IPC on the specified port,
    re-caches flows/index, and returns active database stats.
    """
    data = request.json or {}
    port = int(data.get("port", 8080))
    
    success = init_ipc_connection(port)
    if success:
        try:
            flows_count = len(mapper.flows)
            processes_count = len(list(executor.client.get_descriptors(o.Process)))
            is_empty_db = (flows_count == 0)
            return jsonify({
                "success": True,
                "port": port,
                "flows_count": flows_count,
                "processes_count": processes_count,
                "is_empty_db": is_empty_db
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Connection succeeded but active database statistics query failed: {e}"
            }), 500
    else:
        return jsonify({
            "success": False,
            "error": CONNECTION_ERROR
        }), 500

@app.route('/api/impact-methods', methods=['GET'])
def get_impact_methods():
    """
    Returns a list of all impact assessment methods available in the active openLCA database.
    """
    global CONNECTION_SUCCESS, executor
    if not CONNECTION_SUCCESS or not executor:
        return jsonify([])
    try:
        methods = list(executor.client.get_descriptors(o.ImpactMethod))
        return jsonify([
            {"id": m.id, "name": m.name} for m in methods
        ])
    except Exception as e:
        return jsonify([])

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

def run_mock_optimization(data):
    """
    Simulates optimization calculations when the database is empty or offline.
    """
    items = data.get("items", [])
    param_vals = data.get("parameters", {})
    efficiency = float(param_vals.get("process_efficiency", 1.0))
    loss_factor = float(param_vals.get("loss_factor", 0.0))
    
    total_input_mass = 0.0
    exchanges_list = []
    for item in items:
        flow_name = item.get("flow_name", "Material")
        amount = float(item.get("amount", 1.0))
        unit = item.get("unit", "kg")
        if unit.lower() == "kg":
            total_input_mass += amount
        elif unit.lower() == "g":
            total_input_mass += amount * 1e-3
        elif "water" in flow_name.lower() and unit.lower() in ["m3", "cubic meter"]:
            total_input_mass += amount * 1000.0
            
        exchanges_list.append({
            "id": str(uuid.uuid4()),
            "name": flow_name,
            "amount": amount,
            "unit": unit
        })
        
    scale = (1.0 + loss_factor) / efficiency
    
    baseline_gwp = total_input_mass * 2.8 * scale
    optimized_gwp = total_input_mass * 1.7 * scale
    baseline_acid = total_input_mass * 0.012 * scale
    optimized_acid = total_input_mass * 0.007 * scale
    baseline_water = total_input_mass * 24.5 * scale
    optimized_water = total_input_mass * 15.2 * scale
    baseline_cost = total_input_mass * 1.5 * scale
    optimized_cost = total_input_mass * 1.15 * scale
    
    report = {
        "status": "SUCCESS",
        "process_name": "Product Manufacturing (Simulation Mode)",
        "substituted_from": "Primary virgin materials",
        "substituted_to": "Circular recycled options",
        "metrics": {
            "Global Warming": {
                "baseline": baseline_gwp,
                "baseline_uncertainty": {
                    "stddev": baseline_gwp * 0.08, "ci_low": baseline_gwp * 0.85, "ci_high": baseline_gwp * 1.15, "margin_of_error": baseline_gwp * 0.05
                },
                "optimized": optimized_gwp,
                "optimized_uncertainty": {
                    "stddev": optimized_gwp * 0.09, "ci_low": optimized_gwp * 0.82, "ci_high": optimized_gwp * 1.18, "margin_of_error": optimized_gwp * 0.06
                },
                "difference": optimized_gwp - baseline_gwp,
                "percentage_change": ((optimized_gwp - baseline_gwp) / baseline_gwp * 100) if baseline_gwp > 0 else 0.0,
                "unit": "kg CO2 eq"
            },
            "Acidification": {
                "baseline": baseline_acid,
                "baseline_uncertainty": {
                    "stddev": baseline_acid * 0.07, "ci_low": baseline_acid * 0.86, "ci_high": baseline_acid * 1.14, "margin_of_error": baseline_acid * 0.04
                },
                "optimized": optimized_acid,
                "optimized_uncertainty": {
                    "stddev": optimized_acid * 0.08, "ci_low": optimized_acid * 0.84, "ci_high": optimized_acid * 1.16, "margin_of_error": optimized_acid * 0.05
                },
                "difference": optimized_acid - baseline_acid,
                "percentage_change": ((optimized_acid - baseline_acid) / baseline_acid * 100) if baseline_acid > 0 else 0.0,
                "unit": "kg SO2 eq"
            },
            "Water Consumption": {
                "baseline": baseline_water,
                "baseline_uncertainty": {
                    "stddev": baseline_water * 0.10, "ci_low": baseline_water * 0.80, "ci_high": baseline_water * 1.20, "margin_of_error": baseline_water * 0.07
                },
                "optimized": optimized_water,
                "optimized_uncertainty": {
                    "stddev": optimized_water * 0.12, "ci_low": optimized_water * 0.76, "ci_high": optimized_water * 1.24, "margin_of_error": optimized_water * 0.08
                },
                "difference": optimized_water - baseline_water,
                "percentage_change": ((optimized_water - baseline_water) / baseline_water * 100) if baseline_water > 0 else 0.0,
                "unit": "m3 eq"
            },
            "Feedstock Cost": {
                "baseline": baseline_cost,
                "baseline_uncertainty": {
                    "stddev": baseline_cost * 0.05, "ci_low": baseline_cost * 0.90, "ci_high": baseline_cost * 1.10, "margin_of_error": baseline_cost * 0.03
                },
                "optimized": optimized_cost,
                "optimized_uncertainty": {
                    "stddev": optimized_cost * 0.06, "ci_low": optimized_cost * 0.88, "ci_high": optimized_cost * 1.12, "margin_of_error": optimized_cost * 0.04
                },
                "difference": optimized_cost - baseline_cost,
                "percentage_change": ((optimized_cost - baseline_cost) / baseline_cost * 100) if baseline_cost > 0 else 0.0,
                "unit": "USD"
            }
        }
    }
    
    chart_filename_dark = "optimization_tradeoffs_dark.png"
    chart_filename_light = "optimization_tradeoffs_light.png"
    chart_path_dark = os.path.join(app.root_path, 'static', chart_filename_dark)
    chart_path_light = os.path.join(app.root_path, 'static', chart_filename_light)
    
    LcaVisualizer.generate_tradeoff_chart(report, chart_path_dark, theme="dark")
    LcaVisualizer.generate_tradeoff_chart(report, chart_path_light, theme="light")
    
    # Save a copy in artifacts folder too
    LcaVisualizer.generate_tradeoff_chart(report, "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_dark.png", theme="dark")
    LcaVisualizer.generate_tradeoff_chart(report, "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_light.png", theme="light")
    
    unc_urls_dark = {}
    unc_urls_light = {}
    kpis_mapping = {"Global Warming": "gwp", "Acidification": "acid", "Water Consumption": "water", "Feedstock Cost": "cost"}
    for kpi, short_name in kpis_mapping.items():
        unc_filename_dark = f"uncertainty_{short_name}_dark.png"
        unc_filename_light = f"uncertainty_{short_name}_light.png"
        unc_path_dark = os.path.join(app.root_path, 'static', unc_filename_dark)
        unc_path_light = os.path.join(app.root_path, 'static', unc_filename_light)
        
        LcaVisualizer.generate_uncertainty_chart(report, unc_path_dark, metric_name=kpi, theme="dark")
        LcaVisualizer.generate_uncertainty_chart(report, unc_path_light, metric_name=kpi, theme="light")
        
        # Save to artifacts
        LcaVisualizer.generate_uncertainty_chart(report, f"/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/uncertainty_{short_name}_dark.png", metric_name=kpi, theme="dark")
        LcaVisualizer.generate_uncertainty_chart(report, f"/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/uncertainty_{short_name}_light.png", metric_name=kpi, theme="light")
        
        unc_urls_dark[kpi] = f"/static/{unc_filename_dark}"
        unc_urls_light[kpi] = f"/static/{unc_filename_light}"
        
    tvl_report = {
        "process_name": "Simulated Process", "total_input_mass_kg": total_input_mass, "total_output_mass_kg": total_input_mass,
        "discrepancy_kg": 0.0, "relative_error": 0.0, "is_balanced": True, "is_bulk_balanced": True, "is_elemental_balanced": True, "elemental_discrepancies": {}
    }
    
    justification = f"This calculation was executed in simulation fallback mode because the openLCA database is empty or disconnected. Based on the simulated scaling factor of {scale:.4f}x, circular substitutions yield a simulated {((baseline_gwp - optimized_gwp)/baseline_gwp * 100):.1f}% decrease in Global Warming Potential."
    
    return jsonify({
        "success": True,
        "report": report,
        "tvl_report": tvl_report,
        "justification": justification,
        "exchanges": exchanges_list,
        "temp_proc_id": "simulated-proc",
        "temp_sys_id": "simulated-sys",
        "method_id": "simulated-method",
        "chart_url_dark": f"/static/{chart_filename_dark}",
        "chart_url_light": f"/static/{chart_filename_light}",
        "unc_urls_dark": unc_urls_dark,
        "unc_urls_light": unc_urls_light
    })

def run_mock_pareto(data):
    """
    Simulates Pareto optimization search results when the database is empty or offline.
    """
    items = data.get("items", [])
    weights = data.get("weights") or {}
    
    total_input_mass = 0.0
    for item in items:
        amount = float(item.get("amount", 1.0))
        unit = item.get("unit", "kg")
        if unit.lower() == "kg":
            total_input_mass += amount
        elif unit.lower() == "g":
            total_input_mass += amount * 1e-3
            
    frontier = []
    sub_name = items[0].get("flow_name", "Material") if items else "Material"
    
    ratios_list = [0.0, 0.25, 0.5, 0.75, 1.0]
    for i, r in enumerate(ratios_list):
        eff = 1.2 - (r * 0.2)
        loss = r * 0.05
        scale = (1.0 + loss) / eff
        
        gwp = total_input_mass * (2.8 - r * 1.1) * scale
        acid = total_input_mass * (0.012 - r * 0.005) * scale
        water = total_input_mass * (24.5 - r * 9.3) * scale
        cost = total_input_mass * (1.1 + r * 0.4) * scale
        
        frontier.append({
            "ratios": {f"{sub_name} recycled": r},
            "parameters": {
                "process_efficiency": eff,
                "loss_factor": loss
            },
            "metrics": {
                "GWP": gwp, "Acidification": acid, "Water": water, "Cost": cost
            }
        })
        
    from agentic_lca.decision import TopsisDecisionEngine
    topsis_weights = {
        "GWP": float(weights.get("GWP", 40.0)),
        "Acidification": float(weights.get("Acidification", 15.0)),
        "Water": float(weights.get("Water", 15.0)),
        "Cost": float(weights.get("Cost", 30.0))
    }
    ranked_frontier = TopsisDecisionEngine.rank_alternatives(frontier, topsis_weights)
    
    chart_filename_dark = "pareto_tradeoffs_dark.png"
    chart_filename_light = "pareto_tradeoffs_light.png"
    chart_path_dark = os.path.join(app.root_path, 'static', chart_filename_dark)
    chart_path_light = os.path.join(app.root_path, 'static', chart_filename_light)
    
    pareto_report = {
        "frontier": ranked_frontier,
        "weights": topsis_weights,
        "process_name": "Web-Synthesized Pareto Product (Simulation)"
    }
    LcaVisualizer.generate_tradeoff_chart(pareto_report, chart_path_dark, theme="dark")
    LcaVisualizer.generate_tradeoff_chart(pareto_report, chart_path_light, theme="light")
    
    # Save copies in artifacts directory
    LcaVisualizer.generate_tradeoff_chart(pareto_report, "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_dark.png", theme="dark")
    LcaVisualizer.generate_tradeoff_chart(pareto_report, "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_light.png", theme="light")
    
    return jsonify({
        "success": True,
        "frontier": ranked_frontier,
        "chart_url_dark": f"/static/{chart_filename_dark}",
        "chart_url_light": f"/static/{chart_filename_light}"
    })

def run_mock_compile(data):
    """
    Simulates hierarchical BOM compilation when the database is empty or offline.
    """
    bom_data = data.get("bom", {})
    amount = float(bom_data.get("amount", 1.0))
    unit = bom_data.get("unit", "kg")
    
    exchanges_list = []
    
    def traverse(node):
        name = node.get("name", "Material")
        amt = float(node.get("amount", 1.0))
        ut = node.get("unit", "kg")
        inputs = node.get("inputs", [])
        
        if not inputs:
            exchanges_list.append({
                "id": str(uuid.uuid4()),
                "name": name,
                "amount": amt,
                "unit": ut,
                "is_input": True
            })
        else:
            for child in inputs:
                traverse(child)
                
    traverse(bom_data)
    
    report_metrics = {}
    kpis = {
        "Global Warming": {"val": amount * 2.1, "unit": "kg CO2 eq"},
        "Acidification": {"val": amount * 0.009, "unit": "kg SO2 eq"},
        "Water Consumption": {"val": amount * 18.4, "unit": "m3 eq"},
        "Feedstock Cost": {"val": amount * 1.3, "unit": "USD"}
    }
    
    for kpi, d in kpis.items():
        val = d["val"]
        report_metrics[kpi] = {
            "baseline": val,
            "baseline_uncertainty": {
                "stddev": val * 0.08, "ci_low": val * 0.85, "ci_high": val * 1.15, "margin_of_error": val * 0.05
            },
            "optimized": val,
            "optimized_uncertainty": {
                "stddev": val * 0.08, "ci_low": val * 0.85, "ci_high": val * 1.15, "margin_of_error": val * 0.05
            },
            "difference": 0.0,
            "percentage_change": 0.0,
            "unit": d["unit"]
        }
        
    tvl_report = {
        "process_name": bom_data.get("name", "Simulated Process"),
        "total_input_mass_kg": amount,
        "total_output_mass_kg": amount,
        "discrepancy_kg": 0.0,
        "relative_error": 0.0,
        "is_balanced": True,
        "is_bulk_balanced": True,
        "is_elemental_balanced": True,
        "elemental_discrepancies": {}
    }
    
    return jsonify({
        "success": True,
        "flow_id": "simulated-flow-id",
        "process_id": "simulated-proc-id",
        "system_id": "simulated-sys-id",
        "metrics": report_metrics,
        "exchanges": exchanges_list,
        "tvl_report": tvl_report
    })

@app.route('/api/optimize', methods=['POST'])
def run_optimization():
    """
    Ingests a BOM (either file or custom list of items), runs sensitivity analysis, 
    performs substitution, saves the comparison chart, and returns metrics.
    """
    data = request.json or {}
    items = data.get("items", [])
    param_vals = data.get("parameters", {})
    efficiency = float(param_vals.get("process_efficiency", 1.0))
    loss_factor = float(param_vals.get("loss_factor", 0.0))
    weights = data.get("weights")
    
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
    temp_sys_id = None
    temp_proc_id = None
    temp_flow_id = None
    
    global executor, mapper
    is_mock = not CONNECTION_SUCCESS or not mapper or len(mapper.flows) == 0
    if is_mock:
        try: os.remove(temp_bom_path)
        except: pass
        return run_mock_optimization(data)
        
    try:
        verifier = ThermodynamicVerifier(tolerance=0.01)
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
            exchange.amount_formula = f"{amount} * (1 + loss_factor) / process_efficiency"
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
        
        # Locate method descriptor
        method_id = data.get("method_id")
        if method_id:
            methods = [m for m in executor.client.get_descriptors(o.ImpactMethod) if m.id == method_id]
        else:
            methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
            
        if not methods:
            all_methods = list(executor.client.get_descriptors(o.ImpactMethod))
            methods = [all_methods[0]] if all_methods else []
            
        if not methods:
            raise ValueError("No impact assessment methods found in database.")
        method_desc = methods[0]
        
        # Construct parameter redefinitions
        parameter_redefs = [
            o.ParameterRedef(
                name="process_efficiency",
                value=efficiency,
                context=o.Ref(ref_type=o.RefType.Process, id=temp_proc_id, name="Web-Synthesized Product Manufacturing")
            ),
            o.ParameterRedef(
                name="loss_factor",
                value=loss_factor,
                context=o.Ref(ref_type=o.RefType.Process, id=temp_proc_id, name="Web-Synthesized Product Manufacturing")
            )
        ]
        
        # Ingest custom database parameters overrides from client UI
        custom_params = data.get("custom_parameters", [])
        for cp in custom_params:
            if cp.get("name") and cp.get("value") is not None:
                parameter_redefs.append(
                    o.ParameterRedef(
                        name=cp["name"],
                        value=float(cp["value"]),
                        context=o.Ref(ref_type=o.RefType.Process, id=cp["process_id"], name=cp["process_name"]) if cp.get("process_id") else None
                    )
                )
        
        # 5. Run sensitivities to identify hotspot
        sensitivities = analyzer.analyze_sensitivities(
            process_id=temp_proc_id,
            system_id=temp_sys_id,
            method_id=method_desc.id,
            target_category_query="global warming",
            num_inputs_to_test=5,
            parameter_redefs=parameter_redefs
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
            mapping_scores=mapping_scores,
            parameter_redefs=parameter_redefs
        )
        
        if report.get("status") != "SUCCESS":
            raise RuntimeError(report.get("message", "Substitution evaluation failed."))
            
        # 8. Generate chart and save in static directory
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

        # Generate uncertainty distribution charts for all four KPIs
        kpis_mapping = {
            "Global Warming": "gwp",
            "Acidification": "acid",
            "Water Consumption": "water",
            "Feedstock Cost": "cost"
        }
        
        unc_urls_dark = {}
        unc_urls_light = {}
        
        for kpi, short_name in kpis_mapping.items():
            unc_filename_dark = f"uncertainty_{short_name}_dark.png"
            unc_filename_light = f"uncertainty_{short_name}_light.png"
            
            unc_path_dark = os.path.join(app.root_path, 'static', unc_filename_dark)
            unc_path_light = os.path.join(app.root_path, 'static', unc_filename_light)
            
            LcaVisualizer.generate_uncertainty_chart(report, unc_path_dark, metric_name=kpi, theme="dark")
            LcaVisualizer.generate_uncertainty_chart(report, unc_path_light, metric_name=kpi, theme="light")
            
            # Save copy in artifacts
            LcaVisualizer.generate_uncertainty_chart(
                report, 
                f"/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/uncertainty_{short_name}_dark.png",
                metric_name=kpi,
                theme="dark"
            )
            LcaVisualizer.generate_uncertainty_chart(
                report, 
                f"/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/uncertainty_{short_name}_light.png",
                metric_name=kpi,
                theme="light"
            )
            
            unc_urls_dark[kpi] = f"/static/{unc_filename_dark}"
            unc_urls_light[kpi] = f"/static/{unc_filename_light}"
        
        # 9. LLM justification paragraph
        justification = ""
        if llm_agent.is_ollama_active():
            justification = llm_agent.generate_engineering_justification(report, weights=weights)
            
        # Format exchanges for context list
        exchanges_list = []
        params_dict = {
            "process_efficiency": efficiency,
            "loss_factor": loss_factor
        }
        for ex in process.exchanges:
            if ex.is_input and ex.flow:
                amount = ex.amount
                if ex.amount_formula:
                    expr = ex.amount_formula
                    for name, val in params_dict.items():
                        expr = expr.replace(name, str(val))
                    try:
                        amount = float(eval(expr, {"__builtins__": None}, {}))
                    except:
                        pass
                exchanges_list.append({
                    "id": ex.flow.id,
                    "name": ex.flow.name,
                    "amount": amount,
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
            "chart_url_light": f"/static/{chart_filename_light}",
            "unc_urls_dark": unc_urls_dark,
            "unc_urls_light": unc_urls_light
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

# Global jobs store
jobs = {}

@app.route('/api/autonomous-redesign', methods=['POST'])
def run_autonomous_redesign():
    """
    Starts the LcaAutonomousCoordinator loop in a background thread and returns a job_id.
    """
    import threading
    data = request.json or {}
    items = data.get("items", [])
    goal = data.get("goal", "").strip()
    
    if not items:
        return jsonify({"success": False, "error": "BOM is empty"}), 400
    if not goal:
        return jsonify({"success": False, "error": "Goal description is empty"}), 400
        
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "logs": [],
        "result": None,
        "error": None
    }
    
    def worker():
        def web_logger(msg):
            if job_id in jobs:
                jobs[job_id]["logs"].append(msg)
            
        try:
            coordinator = LcaAutonomousCoordinator(logger=web_logger)
            result = coordinator.run_optimization_goal(items, goal, commit_to_db=True)
            if job_id in jobs:
                jobs[job_id]["result"] = result
                jobs[job_id]["status"] = "completed"
        except Exception as e:
            import traceback
            traceback.print_exc()
            if job_id in jobs:
                jobs[job_id]["error"] = str(e)
                jobs[job_id]["status"] = "failed"
            
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id
    })

@app.route('/api/autonomous-redesign/stream/<job_id>', methods=['GET'])
def stream_autonomous_redesign(job_id):
    """
    Streams the logs and final result of the autonomous loop via Server-Sent Events (SSE).
    """
    import time
    
    def event_stream():
        if job_id not in jobs:
            yield f"data: {json.dumps({'type': 'failed', 'error': 'Job not found'})}\n\n"
            return
            
        job = jobs[job_id]
        last_idx = 0
        
        while True:
            # Check for new logs
            logs = job["logs"]
            if len(logs) > last_idx:
                for msg in logs[last_idx:]:
                    yield f"data: {json.dumps({'type': 'log', 'message': msg})}\n\n"
                last_idx = len(logs)
                
            # Check status
            if job["status"] != "running":
                if job["status"] == "completed":
                    yield f"data: {json.dumps({'type': 'completed', 'result': job['result']})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'failed', 'error': job['error']})}\n\n"
                break
                
            time.sleep(0.1)
            
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/pareto', methods=['POST'])
def run_pareto_optimization():
    """
    Ingests a BOM, constructs a temporary process and product system, 
    runs Pareto optimization across GWP, Acidification, Water, and Cost,
    and returns the list of Pareto-optimal configurations ranked by TOPSIS.
    """
    data = request.json or {}
    items = data.get("items", [])
    num_samples = int(data.get("num_samples", 2000))
    weights = data.get("weights") or {}
    
    temp_sys_id = None
    temp_proc_id = None
    temp_flow_id = None
    
    global executor, mapper
    is_mock = not CONNECTION_SUCCESS or not mapper or len(mapper.flows) == 0
    if is_mock:
        return run_mock_pareto(data)
        
    try:
        verifier = ThermodynamicVerifier(tolerance=0.01)
        cost_registry = CostRegistry()
        optimizer = ParetoOptimizer(executor, mapper, verifier, cost_registry)
        
        # Load units
        unit_map = get_cached_units(executor.client)
        kg_unit = unit_map.get("kg")
        if not kg_unit:
            return jsonify({"success": False, "error": "Kilogram (kg) unit reference not found in database."}), 500
            
        exchanges = []
        total_input_mass = 0.0
        internal_id_counter = 2
        
        # 1. Parse temporary BOM
        for item in items:
            flow_name = item["flow_name"]
            amount = float(item["amount"])
            unit_name = item["unit"]
            
            matches = mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
            if not matches:
                continue
            matched_flow, score = matches[0]
            
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
        module_flow.name = "Web-Synthesized Pareto Product"
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
        process.name = "Web-Synthesized Pareto Manufacturing"
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
        
        # Save process
        executor.client.put(process)
        
        # 4. Compile product system
        sys_ref = executor.client.create_product_system(process)
        if not sys_ref:
            raise RuntimeError("Failed to compile product system.")
        temp_sys_id = sys_ref.id
        
        # Locate method descriptor
        method_id = data.get("method_id")
        if method_id:
            methods = [m for m in executor.client.get_descriptors(o.ImpactMethod) if m.id == method_id]
        else:
            methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
            
        if not methods:
            all_methods = list(executor.client.get_descriptors(o.ImpactMethod))
            methods = [all_methods[0]] if all_methods else []
            
        if not methods:
            raise ValueError("No impact assessment methods found in database.")
        method_desc = methods[0]
        
        # 5. Run Pareto Optimizer
        frontier = optimizer.optimize_process(
            process_id=temp_proc_id,
            system_id=temp_sys_id,
            method_id=method_desc.id,
            num_samples=num_samples
        )
        
        # Rank configurations using TOPSIS
        from agentic_lca.decision import TopsisDecisionEngine
        topsis_weights = {
            "GWP": float(weights.get("GWP", 40.0)),
            "Acidification": float(weights.get("Acidification", 15.0)),
            "Water": float(weights.get("Water", 15.0)),
            "Cost": float(weights.get("Cost", 30.0))
        }
        
        ranked_frontier = TopsisDecisionEngine.rank_alternatives(frontier, topsis_weights)
        
        # Generate Pareto scatter plot and save
        chart_filename_dark = "pareto_tradeoffs_dark.png"
        chart_filename_light = "pareto_tradeoffs_light.png"
        chart_path_dark = os.path.join(app.root_path, 'static', chart_filename_dark)
        chart_path_light = os.path.join(app.root_path, 'static', chart_filename_light)
        
        pareto_report = {
            "frontier": ranked_frontier,
            "weights": topsis_weights,
            "process_name": process.name
        }
        
        LcaVisualizer.generate_tradeoff_chart(pareto_report, chart_path_dark, theme="dark")
        LcaVisualizer.generate_tradeoff_chart(pareto_report, chart_path_light, theme="light")
        
        # Save copies in artifacts directory too!
        LcaVisualizer.generate_tradeoff_chart(
            pareto_report, 
            "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_dark.png",
            theme="dark"
        )
        LcaVisualizer.generate_tradeoff_chart(
            pareto_report, 
            "/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/optimization_tradeoffs_light.png",
            theme="light"
        )
        
        return jsonify({
            "success": True,
            "frontier": ranked_frontier,
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
        
    flow_ref = None
    proc_ref = None
    sys_ref = None
    
    global executor, mapper
    is_mock = not CONNECTION_SUCCESS or not mapper or len(mapper.flows) == 0
    if is_mock:
        return run_mock_compile(data)
        
    try:
        verifier = ThermodynamicVerifier(tolerance=0.01)
        compiler = LcaCompiler(executor, mapper, verifier)
        
        # Compile hierarchical BOM
        flow_ref, proc_ref, sys_ref = compiler.compile_bom(bom_data)
        
        # Locate method descriptor
        method_id = data.get("method_id")
        if method_id:
            methods = [m for m in executor.client.get_descriptors(o.ImpactMethod) if m.id == method_id]
        else:
            methods = executor.find_impact_method("ReCiPe 2016 Midpoint (H)")
            
        if not methods:
            all_methods = list(executor.client.get_descriptors(o.ImpactMethod))
            methods = [all_methods[0]] if all_methods else []
            
        if not methods:
            raise ValueError("No impact assessment methods found in database.")
        method_desc = methods[0]
        
        # Fetch the compiled process details to show exchanges
        proc_obj = executor.client.get(o.Process, proc_ref.id)
        
        # Run mass and elemental verification checks on compiled entity
        _, tvl_report = verifier.verify_mass_balance(proc_obj)
        
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
            "exchanges": exchanges_list,
            "tvl_report": tvl_report
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

@app.route('/api/diagnose', methods=['POST'])
def diagnose_database():
    """
    Scans the database processes associated with the current BOM items
    for structural anomalies (hollow inputs, missing conversion factors, etc.)
    """
    global executor, mapper, CONNECTION_SUCCESS
    if not CONNECTION_SUCCESS or not executor or not mapper:
        return jsonify({"success": False, "error": "openLCA is not connected"}), 500
        
    data = request.json or {}
    items = data.get("items", [])
    
    if not items:
        return jsonify({"success": False, "error": "No BOM items provided to map and scan"}), 400
        
    from agentic_lca.self_healing import DatabaseDoctor
    doctor = DatabaseDoctor(executor)
    
    all_defects = []
    scanned_processes = set()
    
    for item in items:
        flow_name = item.get("flow_name")
        if not flow_name:
            continue
            
        # Search for product flow
        matches = mapper.search(flow_name, top_k=1, flow_type_filter=o.FlowType.PRODUCT_FLOW)
        if not matches:
            continue
            
        flow_desc, score = matches[0]
        try:
            processes = list(executor.client.get_descriptors(o.Process))
            matching_procs = [p for p in processes if flow_name.lower() in p.name.lower()]
            if not matching_procs:
                matching_procs = [p for p in processes if flow_desc.name.lower() in p.name.lower()]
                
            for proc_desc in matching_procs[:2]:
                if proc_desc.id in scanned_processes:
                    continue
                scanned_processes.add(proc_desc.id)
                defects = doctor.diagnose_process(proc_desc.id)
                for d in defects:
                    d["process_name"] = proc_desc.name
                    d["process_id"] = proc_desc.id
                    all_defects.append(d)
        except Exception as e:
            print(f"Error scanning process for {flow_name}: {e}")
            
    return jsonify({
        "success": True,
        "defects": all_defects,
        "scanned_count": len(scanned_processes)
    })

@app.route('/api/heal', methods=['POST'])
def heal_database():
    """
    Applies repairs to the specified database processes/defects.
    """
    global executor, CONNECTION_SUCCESS
    if not CONNECTION_SUCCESS or not executor:
        return jsonify({"success": False, "error": "openLCA is not connected"}), 500
        
    data = request.json or {}
    defects = data.get("defects", [])
    
    if not defects:
        return jsonify({"success": True, "message": "No defects to heal"}), 200
        
    from agentic_lca.self_healing import DatabaseDoctor
    doctor = DatabaseDoctor(executor)
    
    by_process = {}
    for d in defects:
        pid = d.get("process_id")
        if pid:
            if pid not in by_process:
                by_process[pid] = []
            by_process[pid].append(d)
            
    healed_count = 0
    try:
        for pid, process_defects in by_process.items():
            success = doctor.heal_process(pid, process_defects)
            if success:
                healed_count += len(process_defects)
        return jsonify({
            "success": True,
            "message": f"Successfully healed {healed_count} anomalies in the active database.",
            "healed_count": healed_count
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error during database healing: {e}"
        }), 500

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
    param_vals = data.get("parameters", {})
    efficiency = float(param_vals.get("process_efficiency", 1.0))
    loss_factor = float(param_vals.get("loss_factor", 0.0))
    
    if not message:
        return jsonify({"error": "Message is empty"}), 400
        
    global executor, mapper
    if not CONNECTION_SUCCESS:
        return jsonify({"action": "chat", "response": f"I cannot process chat substitutions because openLCA IPC is not connected. Error: {CONNECTION_ERROR}"}), 500
        
    try:
        verifier = ThermodynamicVerifier(tolerance=0.01)
        cost_registry = CostRegistry()
        evaluator = MultiObjectiveEvaluator(executor, verifier, cost_registry)
        llm_agent = LcaLlmAgent()
        weights = data.get("weights")
        command = llm_agent.parse_chat_command(message, exchanges, report, weights=weights)
        action = command.get("action", "chat")
        
        if action == "learn":
            abbreviation = command.get("abbreviation", "").strip()
            standard_name = command.get("standard_name", "").strip()
            if abbreviation and standard_name:
                mapper.save_synonym(abbreviation, standard_name)
                return jsonify({
                    "action": "chat",
                    "response": command.get("response", f"Successfully mapped '{abbreviation}' to '{standard_name}' in the dictionary.")
                })
        
        if action == "substitute" and not (temp_proc_id and temp_sys_id and method_id):
            action = "chat"
            command["action"] = "chat"
            command["response"] = "Please load a case study or compile a hierarchical BOM first before requesting feedstock substitutions. Once loaded, you can request swaps like 'replace steel with scrap steel'."
            
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
                base_amount = float(ex["amount"]) * efficiency / (1.0 + loss_factor)
                
                new_ex = o.Exchange()
                new_ex.is_input = True
                new_ex.flow = o.Ref(ref_type=o.RefType.Flow, id=ex_flow_id, name=ex_flow_name)
                new_ex.amount = base_amount
                new_ex.amount_formula = f"{base_amount} * (1 + loss_factor) / process_efficiency"
                new_ex.unit = o.Ref(ref_type=o.RefType.Unit, id=matched_unit.id, name=matched_unit.name)
                new_ex.flow_property = o.Ref(ref_type=o.RefType.FlowProperty, id="93a60a56-a3c8-11da-a746-0800200b9a66", name="Mass")
                new_ex.internal_id = internal_counter
                internal_counter += 1
                exchanges_objs.append(new_ex)
                
                # Mass sum
                if ex["unit"].lower() == "kg":
                    total_mass += base_amount
                elif ex["unit"].lower() == "g":
                    total_mass += base_amount * 1e-3
                elif "water" in ex_flow_name.lower() and ex["unit"].lower() in ["m3", "cubic meter"]:
                    total_mass += base_amount * 1000.0
            
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
                # Construct parameter redefinitions
                parameter_redefs = [
                    o.ParameterRedef(
                        name="process_efficiency",
                        value=efficiency,
                        context=o.Ref(ref_type=o.RefType.Process, id=rebuild_proc_id, name="Web-Rebuild Manufacturing")
                    ),
                    o.ParameterRedef(
                        name="loss_factor",
                        value=loss_factor,
                        context=o.Ref(ref_type=o.RefType.Process, id=rebuild_proc_id, name="Web-Rebuild Manufacturing")
                    )
                ]
                
                # Ingest custom database parameters overrides from client UI
                custom_params = data.get("custom_parameters", [])
                for cp in custom_params:
                    if cp.get("name") and cp.get("value") is not None:
                        parameter_redefs.append(
                            o.ParameterRedef(
                                name=cp["name"],
                                value=float(cp["value"]),
                                context=o.Ref(ref_type=o.RefType.Process, id=cp["process_id"], name=cp["process_name"]) if cp.get("process_id") else None
                            )
                        )
                
                # Calculate updated metrics
                sub_report = evaluator.evaluate_substitution(
                    process_id=rebuild_proc_id,
                    system_id=sys_ref.id,
                    method_id=method_id,
                    target_flow_id=target_flow_id,
                    substitute_flow_desc=sub_desc,
                    mapping_scores=mapping_scores,
                    parameter_redefs=parameter_redefs
                )
                
                # Save new chart
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

                # Generate new uncertainty distribution charts for all four KPIs
                kpis_mapping = {
                    "Global Warming": "gwp",
                    "Acidification": "acid",
                    "Water Consumption": "water",
                    "Feedstock Cost": "cost"
                }
                
                unc_urls_dark = {}
                unc_urls_light = {}
                
                for kpi, short_name in kpis_mapping.items():
                    unc_filename_dark = f"uncertainty_{short_name}_dark.png"
                    unc_filename_light = f"uncertainty_{short_name}_light.png"
                    
                    unc_path_dark = os.path.join(app.root_path, 'static', unc_filename_dark)
                    unc_path_light = os.path.join(app.root_path, 'static', unc_filename_light)
                    
                    LcaVisualizer.generate_uncertainty_chart(sub_report, unc_path_dark, metric_name=kpi, theme="dark")
                    LcaVisualizer.generate_uncertainty_chart(sub_report, unc_path_light, metric_name=kpi, theme="light")
                    
                    # Save copy in brain artifacts
                    LcaVisualizer.generate_uncertainty_chart(
                        sub_report, 
                        f"/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/uncertainty_{short_name}_dark.png",
                        metric_name=kpi,
                        theme="dark"
                    )
                    LcaVisualizer.generate_uncertainty_chart(
                        sub_report, 
                        f"/Users/somnath.luitel/.gemini/antigravity-cli/brain/0bbe558c-6b76-424c-99dc-0af16d676dc5/uncertainty_{short_name}_light.png",
                        metric_name=kpi,
                        theme="light"
                    )
                    
                    unc_urls_dark[kpi] = f"/static/{unc_filename_dark}"
                    unc_urls_light[kpi] = f"/static/{unc_filename_light}"
                
                # Fetch new LLM justification
                new_just = ""
                if llm_agent.is_ollama_active():
                    new_just = llm_agent.generate_engineering_justification(sub_report, weights=weights)
                    
                # Reconstruct updated exchanges list
                updated_exchanges = []
                params_dict = {
                    "process_efficiency": efficiency,
                    "loss_factor": loss_factor
                }
                for ex_obj in exchanges_objs:
                    amount = ex_obj.amount
                    if ex_obj.amount_formula:
                        expr = ex_obj.amount_formula
                        for name, val in params_dict.items():
                            expr = expr.replace(name, str(val))
                        try:
                            amount = float(eval(expr, {"__builtins__": None}, {}))
                        except:
                            pass
                    updated_exchanges.append({
                        "id": ex_obj.flow.id,
                        "name": ex_obj.flow.name,
                        "amount": amount,
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
                    "chart_url_light": f"/static/{chart_filename_light}?t={int(time.time())}",
                    "unc_urls_dark": unc_urls_dark,
                    "unc_urls_light": unc_urls_light
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
