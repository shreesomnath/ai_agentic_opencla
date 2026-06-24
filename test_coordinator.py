import sys
from agentic_lca.coordinator import LcaAutonomousCoordinator
from agentic_lca import LcaExecutor

def main():
    try:
        # Define a raw Bill of Materials for a new clean tech product
        bom_items = [
            {"flow_name": "glass fibre", "amount": 10.0, "unit": "kg"},
            {"flow_name": "steel, low-alloyed", "amount": 3.0, "unit": "kg"},
            {"flow_name": "polyethylene, high density, granulate", "amount": 1.5, "unit": "kg"}
        ]
        
        # Define the high-level sustainable engineering goal
        goal = "Minimize carbon footprint (GWP) as much as possible, keeping procurement feedstock cost under $10.00"
        
        # Instantiate the autonomous agent coordinator
        print("Initializing Autonomous LCA Coordinator...")
        coordinator = LcaAutonomousCoordinator()
        
        # Run the autonomous loop
        # We will set commit_to_db=True to verify that it modifies and links the database process permanently
        result = coordinator.run_optimization_goal(
            bom_items=bom_items,
            goal_description=goal,
            commit_to_db=True
        )
        
        print("\nVerification Test Completed!")
        if result.get("success"):
            print("Autonomous Loop succeeded in redesigning the process.")
        else:
            print(f"Autonomous Loop failed: {result.get('reason')}")
            
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
