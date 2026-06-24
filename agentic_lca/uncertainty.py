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

    def analyze_sensitivities(self, process_id, system_id, method_id, target_category_query="fossil", num_inputs_to_test=5):
        """
        Runs sensitivity analysis for the top inputs of a process.
        Returns a dictionary of flow names and their corresponding sensitivities (elasticity).
        """
        # 1. Run baseline calculation
        print("Running baseline calculation...")
        baseline_results = self.executor.calculate(system_id, method_id)
        
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
            perturbation = 0.10 # +10% perturbation
            new_amount = orig_amount * (1.0 + perturbation)
            
            print(f"[{idx+1}/{len(input_exchanges)}] Testing sensitivity of '{flow_name}' (perturbing {orig_amount:.4f} -> {new_amount:.4f})...")
            
            try:
                # Apply perturbation in database
                exchange.amount = new_amount
                self.client.put(proc)
                
                # Re-run calculation
                new_results = self.executor.calculate(system_id, method_id)
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
                # Restore original amount in database
                exchange.amount = orig_amount
                self.client.put(proc)
                
        return sensitivities
