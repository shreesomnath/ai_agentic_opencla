import olca_schema as o
import time

class SensitivityAnalyzer:
    """
    Performs sensitivity analysis on OpenLCA product systems by programmatically
    perturbing input exchanges, recalculating impacts, and reporting elasticity.
    """
    def __init__(self, executor):
        self.executor = executor
        self.client = executor.client

    def analyze_sensitivities(self, process_id, system_id, method_id, target_category_query="fossil", num_inputs_to_test=5, parameter_redefs=None):
        """
        Runs sensitivity analysis for the top inputs of a process with optional parameter overrides.
        """
        # 1. Run baseline calculation
        print("Running baseline calculation...")
        baseline_results = self.executor.calculate(system_id, method_id, parameter_redefs=parameter_redefs)
        
        # Find target impact category baseline
        baseline_item = next((r for r in baseline_results if target_category_query.lower() in r["category_name"].lower()), None)
        if not baseline_item:
            # Fallback to first available category
            if baseline_results:
                baseline_item = baseline_results[0]
            else:
                raise ValueError("No baseline impact results returned.")
                
        baseline_val = baseline_item["amount"]
        target_category_name = baseline_item["category_name"]
        print(f"Baseline impact for '{target_category_name}': {baseline_val:.6f} {baseline_item['unit']}")
        
        if baseline_val == 0:
            baseline_val = 1e-10 # Prevent division by zero
            
        # 2. Load process and identify inputs to test
        proc = self.executor.get_process(process_id)
        
        # We test input exchanges that have substantial amounts.
        # Filter exchanges: must be inputs and have a flow name.
        input_exchanges = [e for e in proc.exchanges if e.is_input and e.flow and e.amount > 0]
        
        # Sort inputs by their amount to test the most significant ones first
        input_exchanges = sorted(input_exchanges, key=lambda x: x.amount, reverse=True)[:num_inputs_to_test]
        
        sensitivities = {}
        
        # 3. Perform finite difference perturbations
        for idx, exchange in enumerate(input_exchanges):
            flow_name = exchange.flow.name
            orig_amount = exchange.amount
            orig_formula = exchange.amount_formula
            perturbation = 0.10 # +10% perturbation
            new_amount = orig_amount * (1.0 + perturbation)
            
            print(f"[{idx+1}/{len(input_exchanges)}] Testing sensitivity of '{flow_name}' (perturbing {orig_amount:.4f} -> {new_amount:.4f})...")
            
            try:
                # Apply perturbation in database (temporarily clear formula so openLCA uses perturbed amount)
                exchange.amount_formula = None
                exchange.amount = new_amount
                self.client.put(proc)
                
                # Re-run calculation
                new_results = self.executor.calculate(system_id, method_id, parameter_redefs=parameter_redefs)
                new_item = next((r for r in new_results if r["category_name"] == target_category_name), None)
                
                if new_item:
                    new_val = new_item["amount"]
                    delta_impact_rel = (new_val - baseline_val) / baseline_val
                    # Elasticity = % change in output / % change in input
                    elasticity = delta_impact_rel / perturbation
                    sensitivities[flow_name] = {
                        "elasticity": elasticity,
                        "baseline_amount": orig_amount,
                        "perturbed_amount": new_amount,
                        "unit": exchange.unit.name if exchange.unit else "",
                        "delta_impact_percent": delta_impact_rel * 100
                    }
                    print(f"   -> Resulting impact: {new_val:.6f} (Change: {delta_impact_rel*100:+.4f}%, Elasticity: {elasticity:.4f})")
                else:
                    print("   -> Target category not found in new calculation.")
                    
            except Exception as e:
                print(f"   -> Error perturbing '{flow_name}': {e}")
                
            finally:
                # Restore original amount and formula in database
                exchange.amount_formula = orig_formula
                exchange.amount = orig_amount
                self.client.put(proc)
                
        return sensitivities


class UncertaintyPropagator:
    """
    Performs stochastic error propagation using a Monte Carlo simulation
    based on local linear sensitivities and mapping confidence scores.
    """
    def __init__(self, executor, cost_registry=None):
        self.executor = executor
        self.client = executor.client
        from .multiobjective import CostRegistry
        self.cost_registry = cost_registry if cost_registry else CostRegistry()

    def propagate(self, process_id, system_id, method_id, mapping_scores=None, num_trials=1000, parameter_redefs=None):
        """
        Runs Monte Carlo propagation of inventory mapping uncertainty with optional parameter overrides.
        """
        if mapping_scores is None:
            mapping_scores = {}

        # 1. Run baseline environmental calculation
        print("[Uncertainty] Running baseline calculation...")
        baseline_results = self.executor.calculate(system_id, method_id, parameter_redefs=parameter_redefs)
        
        # We target GWP, Acidification, and Water Consumption
        target_categories = {
            "Global Warming": ["global warming"],
            "Acidification": ["acidification"],
            "Water Consumption": ["water consumption"]
        }
        
        baselines = {}
        category_full_names = {}
        category_units = {}
        
        for kpi, queries in target_categories.items():
            found = None
            for item in baseline_results:
                if any(q in item["category_name"].lower() for q in queries):
                    found = item
                    break
            # Fallback to anything matching if not found
            if not found and baseline_results:
                found = next((item for item in baseline_results if queries[0] in item["category_name"].lower()), None)
            if not found and baseline_results:
                found = baseline_results[0]
            
            if found:
                baselines[kpi] = found["amount"]
                category_full_names[kpi] = found["category_name"]
                category_units[kpi] = found["unit"]
            else:
                baselines[kpi] = 0.0
                category_full_names[kpi] = kpi
                category_units[kpi] = ""

        # Fetch baseline process cost
        proc = self.client.get(o.Process, process_id)
        
        # Calculate baseline cost
        total_cost_baseline = 0.0
        for exchange in proc.exchanges:
            if exchange.is_input and exchange.flow:
                flow_name = exchange.flow.name
                unit_name = exchange.unit.name if exchange.unit else ""
                amount = exchange.amount
                cost = self.cost_registry.get_flow_cost(flow_name, amount, unit_name)
                total_cost_baseline += cost
                
        baselines["Feedstock Cost"] = total_cost_baseline
        category_full_names["Feedstock Cost"] = "Feedstock Cost"
        category_units["Feedstock Cost"] = "USD"

        # 2. Identify input exchanges to perturb
        input_exchanges = [e for e in proc.exchanges if e.is_input and e.flow and e.amount > 0]
        
        # Compute sensitivity coefficients (slopes) for all categories
        coefficients = {kpi: {} for kpi in baselines.keys()}
        
        for idx, exchange in enumerate(input_exchanges):
            flow_id = exchange.flow.id
            flow_name = exchange.flow.name
            orig_amount = exchange.amount
            orig_formula = exchange.amount_formula
            perturbation = 0.10 # +10% perturbation
            new_amount = orig_amount * (1.0 + perturbation)
            delta_x = new_amount - orig_amount
            
            # Cost slope is simply unit cost
            unit_name = exchange.unit.name if exchange.unit else ""
            unit_cost = self.cost_registry.get_flow_cost(flow_name, 1.0, unit_name)
            coefficients["Feedstock Cost"][flow_id] = unit_cost
            
            if delta_x == 0:
                for kpi in target_categories.keys():
                    coefficients[kpi][flow_id] = 0.0
                continue
                
            print(f"[Uncertainty] Computing sensitivity for exchange '{flow_name}'...")
            try:
                # Apply perturbation in database (temporarily clear formula so openLCA uses perturbed amount)
                exchange.amount_formula = None
                exchange.amount = new_amount
                self.client.put(proc)
                
                # Re-calculate
                new_results = self.executor.calculate(system_id, method_id, parameter_redefs=parameter_redefs)
                
                for kpi, queries in target_categories.items():
                    target_name = category_full_names[kpi]
                    new_item = next((r for r in new_results if r["category_name"] == target_name), None)
                    if not new_item:
                        new_item = next((r for r in new_results if any(q in r["category_name"].lower() for q in queries)), None)
                        
                    if new_item:
                        new_val = new_item["amount"]
                        slope = (new_val - baselines[kpi]) / delta_x
                        coefficients[kpi][flow_id] = slope
                    else:
                        coefficients[kpi][flow_id] = 0.0
            except Exception as e:
                print(f"[Uncertainty] Error perturbing exchange '{flow_name}': {e}")
                for kpi in target_categories.keys():
                    coefficients[kpi][flow_id] = 0.0
            finally:
                # Restore original amount and formula in database
                exchange.amount_formula = orig_formula
                exchange.amount = orig_amount
                self.client.put(proc)

        # 3. Perform Monte Carlo loop
        import random
        
        simulated_values = {kpi: [] for kpi in baselines.keys()}
        
        for _ in range(num_trials):
            perturbed_exchanges = {}
            for exchange in input_exchanges:
                flow_id = exchange.flow.id
                orig_amount = exchange.amount
                
                # Fetch mapping score (default to 1.0 if not found, i.e., perfect match)
                score = mapping_scores.get(flow_id, 1.0)
                
                # Standard deviation formula: sigma = amount * (1.0 - score) * 0.15
                sigma = orig_amount * (1.0 - score) * 0.15
                
                # Sample from normal distribution
                if sigma > 0:
                    sampled_amount = random.normalvariate(orig_amount, sigma)
                else:
                    sampled_amount = orig_amount
                    
                # Clip to 0 to prevent physical impossibility
                if sampled_amount < 0:
                    sampled_amount = 0.0
                    
                perturbed_exchanges[flow_id] = sampled_amount
                
            # Compute total impacts for this trial
            for kpi in baselines.keys():
                trial_impact = baselines[kpi]
                for flow_id, sampled_amount in perturbed_exchanges.items():
                    orig_exchange = next(e for e in input_exchanges if e.flow.id == flow_id)
                    slope = coefficients[kpi].get(flow_id, 0.0)
                    trial_impact += slope * (sampled_amount - orig_exchange.amount)
                simulated_values[kpi].append(trial_impact)
                
        # 4. Compute statistics
        stats = {}
        for kpi in baselines.keys():
            vals = sorted(simulated_values[kpi])
            mean_val = sum(vals) / len(vals)
            
            # Variance and standard deviation
            variance = sum((x - mean_val) ** 2 for x in vals) / (len(vals) - 1) if len(vals) > 1 else 0.0
            stddev = variance ** 0.5
            
            # 95% Confidence Interval
            ci_low_idx = int(0.025 * len(vals))
            ci_high_idx = int(0.975 * len(vals)) - 1
            ci_low = vals[ci_low_idx] if vals else mean_val
            ci_high = vals[ci_high_idx] if vals else mean_val
            
            margin_of_error = (ci_high - ci_low) / 2
            
            stats[kpi] = {
                "baseline": baselines[kpi],
                "mean": mean_val,
                "stddev": stddev,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "margin_of_error": margin_of_error,
                "unit": category_units[kpi],
                "trials": vals
            }
            
        return stats

