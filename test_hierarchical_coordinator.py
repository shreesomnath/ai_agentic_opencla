import sys
import time
from agentic_lca.coordinator import LcaAutonomousCoordinator
from agentic_lca import LcaExecutor

def main():
    try:
        # Define a hierarchical BOM for a wind turbine blade structure
        bom_dict = {
            "name": "Test Nested Wind Turbine Blade Model",
            "amount": 1000.0,
            "unit": "kg",
            "inputs": [
                {
                    "name": "Custom Structural Glass Assembly",
                    "amount": 600.0,
                    "unit": "kg",
                    "inputs": [
                        {"name": "glass fibre", "amount": 550.0, "unit": "kg"},
                        {"name": "polyethylene, high density, granulate", "amount": 50.0, "unit": "kg"}
                    ]
                },
                {
                    "name": "Custom Reinforced Core Assembly",
                    "amount": 400.0,
                    "unit": "kg",
                    "inputs": [
                        {"name": "steel, low-alloyed", "amount": 380.0, "unit": "kg"},
                        {"name": "tap water", "amount": 20.0, "unit": "kg"}
                    ]
                }
            ]
        }
        
        goal = "Minimize carbon footprint (GWP) as much as possible, keeping procurement feedstock cost under $20.00"
        
        print("Initializing Autonomous LCA Coordinator for Hierarchical BOM...")
        coordinator = LcaAutonomousCoordinator()
        
        start_time = time.time()
        
        # Run autonomous loop
        # We will commit changes to db to verify the end-to-end recursive writes
        result = coordinator.run_optimization_goal(
            bom_items=bom_dict,
            goal_description=goal,
            commit_to_db=True
        )
        
        elapsed = time.time() - start_time
        print("\n" + "="*50)
        print("Hierarchical Integration Test Verification Completed!")
        print("="*50)
        
        if result.get("success"):
            print("Autonomous Loop successfully optimized the nested hierarchical assembly!")
            print(f"Baseline GWP:  {result.get('baseline_gwp'):.6f} kg CO2 eq")
            print(f"Optimized GWP: {result.get('optimized_gwp'):.6f} kg CO2 eq")
            print(f"Baseline Cost: ${result.get('baseline_cost'):.2f}")
            print(f"Optimized Cost: ${result.get('optimized_cost'):.2f}")
            print(f"Ratios: {result.get('optimal_ratios')}")
            print(f"Total time: {elapsed:.2f}s")
        else:
            print(f"Autonomous Loop failed: {result.get('reason')}")
            
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
