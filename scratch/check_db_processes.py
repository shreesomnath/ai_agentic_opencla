import olca_ipc as ipc
import olca_schema as o

client = ipc.Client(8080)
processes = list(client.get_descriptors(o.Process))
print(f"Total processes: {len(processes)}")

# Print custom processes
custom_processes = [p for p in processes if "Custom" in p.name]
print(f"Found {len(custom_processes)} custom processes:")
for p in custom_processes:
    print(f" - Name: '{p.name}', ID: {p.id}")
