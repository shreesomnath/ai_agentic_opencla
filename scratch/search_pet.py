import olca_ipc as ipc
import olca_schema as o

client = ipc.Client(8080)
flows = list(client.get_descriptors(o.Flow))

matches = [f for f in flows if "terephthalate" in f.name.lower() or "polyethylene" in f.name.lower()]
print(f"Found {len(matches)} matching flows:")
for m in matches[:30]:
    print(f" - '{m.name}' (Category: {m.category})")
