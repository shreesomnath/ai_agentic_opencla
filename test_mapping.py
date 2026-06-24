from agentic_lca import LcaExecutor, FlowMapper
import time

def main():
    try:
        executor = LcaExecutor()
        
        # Initialize FlowMapper (this loads and indexes all flows)
        start_time = time.time()
        mapper = FlowMapper(executor)
        print(f"Indexing took {time.time() - start_time:.2f} seconds.")
        
        # Queries to test
        queries = [
            "silicone",
            "purified silicon",
            "polyethylene",
            "tap water"
        ]
        
        for q in queries:
            print(f"\n--- Search results for: '{q}' ---")
            search_start = time.time()
            results = mapper.search(q, top_k=5)
            search_time = time.time() - search_start
            
            for idx, (flow_desc, score) in enumerate(results):
                print(f" {idx+1}. Flow: '{flow_desc.name}'")
                print(f"    Category: {flow_desc.category}")
                print(f"    Flow ID:  {flow_desc.id}")
                print(f"    Score:    {score:.4f}")
            print(f"Search completed in {search_time*1000:.2f} ms.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
