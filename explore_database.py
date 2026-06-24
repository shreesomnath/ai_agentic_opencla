import olca_ipc as ipc
import olca_schema as o

def main():
    try:
        print("Connecting to OpenLCA IPC server on port 8080...")
        client = ipc.Client(port=8080)
        
        # 1. Get database info or descriptors count
        print("\n--- Descriptors Counts ---")
        for cls in [o.Process, o.ProductSystem, o.ImpactMethod, o.Flow, o.FlowProperty, o.UnitGroup]:
            try:
                descriptors = list(client.get_descriptors(cls))
                print(f" - {cls.__name__}: {len(descriptors)}")
            except Exception as ex:
                print(f" - Could not get {cls.__name__}: {ex}")
                
        # 2. Print a sample of processes
        print("\n--- Sample Processes (first 10) ---")
        processes = list(client.get_descriptors(o.Process))
        for p in processes[:10]:
            print(f" - {p.name} (ID: {p.id})")
            
        # 3. Print a sample of product systems
        print("\n--- Product Systems ---")
        systems = list(client.get_descriptors(o.ProductSystem))
        for s in systems:
            print(f" - {s.name} (ID: {s.id})")

        # 4. Print available LCIA methods
        print("\n--- LCIA Methods (first 10) ---")
        methods = list(client.get_descriptors(o.ImpactMethod))
        for m in methods[:10]:
            print(f" - {m.name} (ID: {m.id})")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
