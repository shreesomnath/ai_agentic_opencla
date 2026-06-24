import olca_ipc as ipc
import olca_schema as o

try:
    print("Connecting to OpenLCA IPC server on port 8080...")
    client = ipc.Client(port=8080)
    
    # Check if we can fetch descriptors
    methods = list(client.get_descriptors(o.ImpactMethod))
    print(f"\nSuccessfully connected! Found {len(methods)} LCIA Methods in the database:")
    for method in methods[:10]: # Print first 10 methods
        print(f" - {method.name} (ID: {method.id})")
        
    processes = list(client.get_descriptors(o.Process))
    print(f"\nFound {len(processes)} Processes in the database. Examples:")
    for process in processes[:10]: # Print first 10 processes
        print(f" - {process.name} (ID: {process.id})")

except Exception as e:
    print(f"\nError connecting to IPC server: {e}")
    print("Please make sure OpenLCA is open, a database is active, and the IPC server is running on port 8080.")
