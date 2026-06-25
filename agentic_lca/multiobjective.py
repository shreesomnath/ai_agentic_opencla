import olca_schema as o
import time

class CostRegistry:
    """
    Local financial cost registry for technosphere inputs.
    Allows mapping flows to unit costs (USD/unit) for economic trade-off analysis.
    """
    def __init__(self):
        # Default cost dictionary (USD per unit)
        self.costs = {
            "polyethylene, high density, granulate, recycled": 1.15,             # USD/kg
            "polyethylene, high density, granulate": 1.68,                      # USD/kg
            "packaging film, low density polyethylene": 1.95,                   # USD/kg
            "glass fibre": 1.80,                                                # USD/kg
            "glass cullet, sorted": 0.25,                                       # USD/kg
            "glass cullet": 0.25,                                               # USD/kg
            "steel, chromium steel 18/8": 0.90,                                 # USD/kg
            "scrap steel": 0.30,                                                # USD/kg
            "silicon tetrachloride": 1.45,                                      # USD/kg
            "tap water": 0.0015,                                                # USD/kg
            "compressed air, 600 kPa gauge": 0.04,                               # USD/m3
            "electricity, low voltage": 0.12,                                   # USD/kWh
            "silicone product": 2.50,                                           # USD/kg
            "Used crystalline silicon solar panel, end-of-life": 0.0            # Waste input
        }


    def get_flow_cost(self, flow_name, amount, unit_name):
        """
        Estimates the cost of a flow given its name, amount, and unit.
        Returns the cost in USD, or 0.0 if not registered.
        """
        flow_name_lower = flow_name.lower()
        # Sort keys by length in descending order to match the most specific names first
        sorted_keys = sorted(self.costs.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key.lower() in flow_name_lower:
                return amount * self.costs[key]
        return 0.0



class MultiObjectiveEvaluator:
    """
    Calculates multi-indicator environmental and economic trade-offs 
    (Global Warming, Terrestrial Acidification, Water Consumption, and Cost)
    for feedstock substitution scenarios.
    """
    def __init__(self, executor, verifier, cost_registry=None):
        self.executor = executor
        self.client = executor.client
        self.verifier = verifier
        self.cost_registry = cost_registry if cost_registry else CostRegistry()

    def calculate_process_cost(self, process):
        """
        Calculates the total technosphere input cost for a process.
        """
        total_cost = 0.0
        for exchange in process.exchanges:
            if exchange.is_input and exchange.flow:
                flow_name = exchange.flow.name
                unit_name = exchange.unit.name if exchange.unit else ""
                amount = exchange.amount
                cost = self.cost_registry.get_flow_cost(flow_name, amount, unit_name)
                total_cost += cost
        return total_cost

    def evaluate_substitution(self, process_id, system_id, method_id, target_flow_id, substitute_flow_desc, mapping_scores=None, parameter_redefs=None):
        """
        Evaluates the trade-offs of substituting a process input exchange with an alternative,
        propagating mapping uncertainty through a Monte Carlo simulation.
        
        Parameters:
          process_id: ID of the process to modify
          system_id: ID of the product system to calculate
          method_id: ID of the multi-impact assessment method (e.g. ReCiPe 2016 Midpoint H)
          target_flow_id: ID of the flow to replace in the process exchanges
          substitute_flow_desc: FlowDescriptor of the substitute flow
          mapping_scores: Dictionary of flow IDs to mapping confidence scores
          parameter_redefs: List of parameter overrides to apply during calculations
          
        Returns:
          A dictionary containing comparison reports for GWP, Acidification, Water, and Cost.
        """
        from .uncertainty import UncertaintyPropagator

        # 1. Fetch process details
        proc = self.client.get(o.Process, process_id)
        target_exchange = None
        for ex in proc.exchanges:
            if ex.is_input and ex.flow and ex.flow.id == target_flow_id:
                target_exchange = ex
                break
                
        if not target_exchange:
            raise ValueError(f"Exchange with flow ID {target_flow_id} not found in process exchanges.")
            
        original_flow_ref = target_exchange.flow

        # 2. Baseline Environmental impacts & uncertainty propagation
        print("[MOE] Running baseline environmental calculation & uncertainty propagation...")
        propagator = UncertaintyPropagator(self.executor, self.cost_registry)
        baseline_stats = propagator.propagate(
            process_id=process_id,
            system_id=system_id,
            method_id=method_id,
            mapping_scores=mapping_scores,
            num_trials=1000,
            parameter_redefs=parameter_redefs
        )
        
        # 3. TVL Check for Substitution
        print("[MOE] Running TVL mass balance check for substitute flow...")
        _, baseline_tvl = self.verifier.verify_mass_balance(proc)
        
        # Update flow in-memory for TVL check
        substitute_ref = o.Ref(
            ref_type=o.RefType.Flow,
            id=substitute_flow_desc.id,
            name=substitute_flow_desc.name,
            ref_unit=substitute_flow_desc.ref_unit
        )
        target_exchange.flow = substitute_ref
        
        _, substituted_tvl = self.verifier.verify_mass_balance(proc)
        
        # Verify differential mass conservation
        mass_diff_input = abs(substituted_tvl['total_input_mass_kg'] - baseline_tvl['total_input_mass_kg'])
        mass_diff_output = abs(substituted_tvl['total_output_mass_kg'] - baseline_tvl['total_output_mass_kg'])
        is_substitution_valid = (mass_diff_input < 0.01) and (mass_diff_output < 0.01)
        
        # Check elemental difference between substitute and original flow
        orig_comp = self.verifier.get_flow_composition(original_flow_ref.name)
        sub_comp = self.verifier.get_flow_composition(substitute_flow_desc.name)
        
        elemental_message = ""
        if orig_comp and sub_comp:
            elemental_discrepancy = 0.0
            all_elements = set(orig_comp.keys()) | set(sub_comp.keys())
            for el in all_elements:
                elemental_discrepancy += abs(orig_comp.get(el, 0.0) - sub_comp.get(el, 0.0))
                
            if elemental_discrepancy > 0.20:
                is_substitution_valid = False
                elemental_message = f"Elemental profile mismatch of {elemental_discrepancy*100:.1f}% (e.g. cannot swap '{original_flow_ref.name}' with '{substitute_flow_desc.name}')."
        
        if not is_substitution_valid:
            # Revert in-memory reference
            target_exchange.flow = original_flow_ref
            msg = elemental_message if elemental_message else f"Mass not conserved. Input delta: {mass_diff_input:.4f} kg, Output delta: {mass_diff_output:.4f} kg"
            return {
                "status": "REJECTED_TVL_FAILED",
                "message": msg,
                "baseline": {},
                "optimized": {}
            }
            
        # 4. Apply substitution to DB and compile a temporary system
        print("[MOE] Applying substitution to database & compiling temporary product system...")
        self.client.put(proc)
        
        # Fetch full product system definition to resolve new supply chain links
        sys_obj = self.client.get(o.ProductSystem, system_id)
        temp_sys = self.client.create_product_system(sys_obj.ref_process)
        
        opt_stats = {}
        try:
            # Calculate optimized environmental impacts & uncertainty propagation
            print("[MOE] Running optimized environmental calculation & uncertainty propagation...")
            opt_stats = propagator.propagate(
                process_id=process_id,
                system_id=temp_sys.id,
                method_id=method_id,
                mapping_scores=mapping_scores,
                num_trials=1000,
                parameter_redefs=parameter_redefs
            )
            
        finally:
            # Revert flow back to original in the database
            print("[MOE] Cleaning up and restoring database state...")
            target_exchange.flow = original_flow_ref
            self.client.put(proc)
            # Delete temporary product system
            self.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys.id))
            
        # Compile trade-off report
        report = {
            "status": "SUCCESS",
            "process_name": proc.name,
            "substituted_from": original_flow_ref.name,
            "substituted_to": substitute_flow_desc.name,
            "metrics": {
                "Global Warming": self._format_metric(baseline_stats["Global Warming"], opt_stats["Global Warming"]),
                "Acidification": self._format_metric(baseline_stats["Acidification"], opt_stats["Acidification"]),
                "Water Consumption": self._format_metric(baseline_stats["Water Consumption"], opt_stats["Water Consumption"]),
                "Feedstock Cost": self._format_metric(baseline_stats["Feedstock Cost"], opt_stats["Feedstock Cost"])
            }
        }
        
        return report

    def _find_impact(self, results, substring):
        """Helper to find impact amount by name substring."""
        item = next((r for r in results if substring.lower() in r["category_name"].lower()), None)
        return item["amount"] if item else 0.0

    def _format_metric(self, baseline_stat, opt_stat):
        """Formats baseline, optimized, delta, percentage change, and uncertainty ranges for a metric."""
        base_val = baseline_stat["baseline"]
        opt_val = opt_stat["baseline"]
        diff = opt_val - base_val
        rel_change_pct = (diff / base_val * 100) if base_val > 0 else 0.0
        return {
            "baseline": base_val,
            "baseline_uncertainty": {
                "stddev": baseline_stat["stddev"],
                "ci_low": baseline_stat["ci_low"],
                "ci_high": baseline_stat["ci_high"],
                "margin_of_error": baseline_stat["margin_of_error"],
                "trials": baseline_stat.get("trials", [])
            },
            "optimized": opt_val,
            "optimized_uncertainty": {
                "stddev": opt_stat["stddev"],
                "ci_low": opt_stat["ci_low"],
                "ci_high": opt_stat["ci_high"],
                "margin_of_error": opt_stat["margin_of_error"],
                "trials": opt_stat.get("trials", [])
            },
            "difference": diff,
            "percentage_change": rel_change_pct,
            "unit": baseline_stat["unit"]
        }
