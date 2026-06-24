import random
import olca_schema as o

class ParetoOptimizer:
    """
    Executes multi-objective feedstock blending optimization using linear sensitivity
    surrogate models to find the Pareto-optimal frontier across multiple indicators.
    """
    def __init__(self, executor, mapper, verifier, cost_registry=None):
        self.executor = executor
        self.client = executor.client
        self.mapper = mapper
        self.verifier = verifier
        from .multiobjective import CostRegistry
        self.cost_registry = cost_registry if cost_registry else CostRegistry()

    def optimize_process(self, process_id, system_id, method_id, num_samples=2000):
        """
        Builds a linear surrogate model for all feedstock substitutions and returns the Pareto frontier.
        """
        proc = self.client.get(o.Process, process_id)
        
        # 1. Identify input exchanges that represent physical material feedstocks
        input_exchanges = []
        for e in proc.exchanges:
            if not (e.is_input and e.flow and e.amount > 0):
                continue
            unit_name = (e.unit.name or "").lower() if e.unit else ""
            flow_name = (e.flow.name or "").lower()
            
            # Keep only mass-based physical feedstocks
            if unit_name not in ["kg", "g", "t", "ton", "kg(active substance)"]:
                continue
            # Exclude services, transport, energy, and water
            if any(term in flow_name for term in ["electricity", "transport", "freight", "lorry", "air", "water", "heat", "steam", "transmission", "distribution"]):
                continue
            input_exchanges.append(e)
        
        # 2. For each feedstock, find its recycled/secondary substitute flow descriptor
        substitutes = {}
        for ex in input_exchanges:
            flow_name = ex.flow.name
            flow_id = ex.flow.id
            
            flow_lower = flow_name.lower()
            if "recycled" in flow_lower or "cullet" in flow_lower or "scrap" in flow_lower:
                continue # Already recycled
                
            # Search query
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
                print(f"[Pareto] Found substitute for '{flow_name}': '{sub_desc.name}'")

        if not substitutes:
            print("[Pareto Warning] No substitutable feedstocks identified.")
            return []

        # 3. Calculate baseline metrics
        baseline_results = self.executor.calculate(system_id, method_id)
        
        target_categories = {
            "GWP": ["global warming"],
            "Acidification": ["acidification"],
            "Water": ["water consumption"]
        }
        
        baselines = {}
        category_full_names = {}
        
        for kpi, queries in target_categories.items():
            found = next((item for item in baseline_results if any(q in item["category_name"].lower() for q in queries)), None)
            if found:
                baselines[kpi] = found["amount"]
                category_full_names[kpi] = found["category_name"]
            else:
                baselines[kpi] = 0.0
                category_full_names[kpi] = kpi
                
        # Baseline Cost
        total_cost_baseline = 0.0
        for exchange in proc.exchanges:
            if exchange.is_input and exchange.flow:
                total_cost_baseline += self.cost_registry.get_flow_cost(exchange.flow.name, exchange.amount, exchange.unit.name if exchange.unit else "")
        baselines["Cost"] = total_cost_baseline

        # 4. Calculate marginal impacts for both virgin and recycled options
        delta_impacts = {}
        
        for flow_id, sub_desc in substitutes.items():
            exchange = next(e for e in input_exchanges if e.flow.id == flow_id)
            orig_flow_ref = exchange.flow
            amount = exchange.amount
            
            substitute_ref = o.Ref(
                ref_type=o.RefType.Flow,
                id=sub_desc.id,
                name=sub_desc.name,
                ref_unit=sub_desc.ref_unit
            )
            
            # Apply substitution temporarily in DB
            exchange.flow = substitute_ref
            self.client.put(proc)
            
            # Re-compile temporary product system to evaluate actual footprint
            sys_obj = self.client.get(o.ProductSystem, system_id)
            temp_sys = self.client.create_product_system(sys_obj.ref_process)
            
            delta_impacts[flow_id] = {}
            
            try:
                opt_results = self.executor.calculate(temp_sys.id, method_id)
                for kpi, queries in target_categories.items():
                    opt_item = next((r for r in opt_results if r["category_name"] == category_full_names[kpi]), None)
                    if not opt_item:
                        opt_item = next((r for r in opt_results if any(q in r["category_name"].lower() for q in queries)), None)
                    opt_val = opt_item["amount"] if opt_item else baselines[kpi]
                    
                    delta_impacts[flow_id][kpi] = opt_val - baselines[kpi]
            except Exception as e:
                print(f"[Pareto] Error calculating footprint of substitute '{sub_desc.name}': {e}")
                for kpi in target_categories.keys():
                    delta_impacts[flow_id][kpi] = 0.0
            finally:
                # Cleanup temporary product system
                try: self.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys.id))
                except: pass
                # Restore baseline exchange
                exchange.flow = orig_flow_ref
                self.client.put(proc)

            # Cost change for 100% swap
            unit_name = exchange.unit.name if exchange.unit else ""
            virgin_cost = self.cost_registry.get_flow_cost(orig_flow_ref.name, amount, unit_name)
            recycled_cost = self.cost_registry.get_flow_cost(sub_desc.name, amount, unit_name)
            delta_impacts[flow_id]["Cost"] = recycled_cost - virgin_cost

        # 5. Monte Carlo Sampling to find Pareto frontier
        sampled_points = []
        
        for i in range(num_samples):
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
                flow_name = next(e.flow.name for e in input_exchanges if e.flow.id == flow_id)
                ratios_named[flow_name] = r
                
            sampled_points.append({
                "ratios": ratios_named,
                "metrics": pt_metrics
            })
            
        # Extract Pareto frontier
        frontier = get_pareto_frontier(sampled_points)
        print(f"[Pareto] Sampled {num_samples} points. Identified {len(frontier)} Pareto-optimal configurations.")
        return frontier

def get_pareto_frontier(points):
    pareto_frontier = []
    for i, p1 in enumerate(points):
        dominated = False
        y1 = p1["metrics"]
        
        for j, p2 in enumerate(points):
            if i == j:
                continue
            y2 = p2["metrics"]
            
            if (y2["GWP"] <= y1["GWP"] and 
                y2["Acidification"] <= y1["Acidification"] and 
                y2["Water"] <= y1["Water"] and 
                y2["Cost"] <= y1["Cost"] and 
                (y2["GWP"] < y1["GWP"] or 
                 y2["Acidification"] < y1["Acidification"] or 
                 y2["Water"] < y1["Water"] or 
                 y2["Cost"] < y1["Cost"])):
                dominated = True
                break
                
        if not dominated:
            pareto_frontier.append(p1)
            
    return pareto_frontier
