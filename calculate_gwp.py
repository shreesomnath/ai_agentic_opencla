import olca_ipc as ipc
import olca_schema as o
import time

def main():
    try:
        print("Connecting to OpenLCA IPC server on port 8080...")
        client = ipc.Client(port=8080)
        
        # 1. Search for the pre-existing product system
        print("Searching for product system 'Mechanical recycling of used c-Si panel - US-TRE'...")
        systems = list(client.get_descriptors(o.ProductSystem))
        target_system = next((s for s in systems if "Mechanical recycling" in s.name), None)
        
        should_delete_system = False
        
        if target_system:
            print(f"Found existing product system: {target_system.name} (ID: {target_system.id})")
        else:
            print("Product system not found. Let's create one from a process...")
            processes = list(client.get_descriptors(o.Process))
            target_proc = next((p for p in processes if "silicone product production" in p.name), None)
            if not target_proc:
                if processes:
                    target_proc = processes[0]
                else:
                    print("No processes found in database.")
                    return
            print(f"Creating new product system for '{target_proc.name}'...")
            target_system = client.create_product_system(target_proc)
            if not target_system:
                print("Failed to create product system.")
                return
            should_delete_system = True
            print(f"Product System created: ID {target_system.id}")

        # 2. Find the impact assessment method
        print("Searching for 'IPCC 2013 GWP 100a' impact method...")
        methods = list(client.get_descriptors(o.ImpactMethod))
        target_method = next((m for m in methods if "IPCC 2013 GWP 100a" in m.name), None)
        
        if not target_method:
            print("IPCC 2013 GWP 100a not found. Using the first available impact method...")
            if methods:
                target_method = methods[0]
            else:
                print("No impact methods found in database.")
                return
                
        print(f"Target LCIA Method: {target_method.name} (ID: {target_method.id})")
        
        # 3. Configure the calculation setup
        print("Setting up calculation...")
        setup = o.CalculationSetup()
        setup.target = o.Ref(ref_type=o.RefType.ProductSystem, id=target_system.id)
        setup.impact_method = o.Ref(ref_type=o.RefType.ImpactMethod, id=target_method.id)
        setup.amount = 1.0 # 1.0 functional unit (e.g., 1 panel recycled)
        
        # 4. Run the calculation
        print("Executing LCA calculation in OpenLCA...")
        result = client.calculate(setup)
        
        # 5. Poll for results to be ready
        print("Waiting for calculation to complete...")
        start_time = time.time()
        while True:
            state = result.get_state()
            if state.error:
                print(f"Calculation error: {state.error}")
                return
            if state.is_ready:
                print(f"Calculation complete (took {time.time() - start_time:.2f}s)!")
                break
            if time.time() - start_time > 60:
                print("Timeout: Calculation took too long.")
                return
            time.sleep(0.5)
        
        # 6. Print results
        print("\n=== Calculation Results ===")
        impacts = result.get_total_impacts()
        if not impacts:
            print("No impact values returned. Check if the product system contains links and flows.")
        else:
            for val in impacts:
                category = val.impact_category
                unit_str = category.ref_unit if category.ref_unit else ""
                print(f" - {category.name}: {val.amount:.6f} {unit_str}")
                
        # Clean up database resources
        print("\nCleaning up calculation resources...")
        result.dispose()
        if should_delete_system:
            print("Deleting temporary product system...")
            client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=target_system.id))
        print("Done!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
