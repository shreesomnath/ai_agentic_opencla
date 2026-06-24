import olca_ipc as ipc
import olca_schema as o

def main():
    try:
        print("Connecting to OpenLCA IPC server on port 8080...")
        client = ipc.Client(port=8080)
        
        print("\n--- Advanced Descriptors Counts ---")
        advanced_classes = [
            (o.Parameter, "Parameters (Global/Process)"),
            (o.Epd, "EPDs (Environmental Product Declarations)"),
            (o.Project, "Projects"),
            (o.Result, "Saved Results"),
            (o.SocialIndicator, "Social Indicators"),
            (o.Source, "Sources / Literature References"),
            (o.Location, "Locations"),
            (o.DQSystem, "Data Quality Systems")
        ]
        
        for cls, label in advanced_classes:
            try:
                descriptors = list(client.get_descriptors(cls))
                print(f" - {label} ({cls.__name__}): {len(descriptors)}")
            except Exception as ex:
                print(f" - Could not get {label}: {ex}")
                
        # Let's inspect some samples of locations
        print("\n--- Sample Locations (first 10) ---")
        locations = list(client.get_descriptors(o.Location))
        for loc in locations[:10]:
            print(f" - {loc.name} (Code: {getattr(loc, 'code', 'N/A')} | ID: {loc.id})")
            
        # Let's see if there are any global parameters
        print("\n--- Sample Parameters (first 10) ---")
        params = list(client.get_descriptors(o.Parameter))
        for p in params[:10]:
            print(f" - {p.name} (ID: {p.id})")
            
        # Let's check some literature sources
        print("\n--- Sample Sources / References (first 10) ---")
        sources = list(client.get_descriptors(o.Source))
        for s in sources[:10]:
            print(f" - {s.name} (ID: {s.id})")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
