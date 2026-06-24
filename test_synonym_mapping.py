import time
from agentic_lca import LcaExecutor, FlowMapper

def main():
    try:
        executor = LcaExecutor()
        
        print("Initializing FlowMapper and building TF-IDF mapping index...")
        start_time = time.time()
        mapper = FlowMapper(executor)
        print(f"Indexing completed in {time.time() - start_time:.2f} seconds.\n")
        
        # Test abbreviation and synonym queries
        test_queries = [
            "PET",
            "HDPE",
            "cullet",
            "scrap steel"
        ]
        
        for q in test_queries:
            print("="*60)
            print(f"Query: '{q}'")
            print("="*60)
            
            # Print intermediate standard name expansions if LLM is active
            if mapper.llm_agent.is_ollama_active():
                try:
                    expansions = mapper.llm_agent.expand_material_query(q)
                    print(f"Standard Expansions (LLM): {expansions}")
                except Exception as e:
                    print(f"Expansion Error: {e}")
            
            search_start = time.time()
            results = mapper.search(q, top_k=5)
            search_time = time.time() - search_start
            
            print("\nMatched Flows in Database:")
            for idx, (flow_desc, score) in enumerate(results):
                print(f" {idx+1}. Flow: '{flow_desc.name}'")
                print(f"    Category: {flow_desc.category}")
                print(f"    Flow ID:  {flow_desc.id}")
                print(f"    Score:    {score:.4f}")
            print(f"\nSearch and re-ranking completed in {search_time:.2f} seconds.\n")
            
    except Exception as e:
        print(f"Error during synonym mapping test: {e}")

if __name__ == "__main__":
    main()
