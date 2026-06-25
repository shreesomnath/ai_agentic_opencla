import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agentic_lca import LcaExecutor, FlowMapper

def main():
    executor = LcaExecutor()
    mapper = FlowMapper(executor)
    
    query = "solar silicon"
    print(f"=== Debugging Query: '{query}' ===")
    
    # 1. LLM Expansion
    expansions = mapper.llm_agent.expand_material_query(query)
    print(f"LLM Expansions: {expansions}")
    
    # Let's run the search with and without LLM re-ranking
    # First, run with LLM active (Neuro-Symbolic)
    print("\n--- Neuro-Symbolic Search (With Re-ranking) ---")
    results = mapper.search(query, top_k=5)
    for idx, (flow_desc, score) in enumerate(results):
        print(f" {idx+1}. '{flow_desc.name}' (ID: {flow_desc.id}) - Score: {score:.4f}")
        
    # Second, run without LLM active
    print("\n--- Intermediate Search (Without Re-ranking, but with expansions) ---")
    mapper.llm_agent.is_ollama_active = lambda: False
    results_no_rerank = mapper.search(query, top_k=5)
    for idx, (flow_desc, score) in enumerate(results_no_rerank):
        print(f" {idx+1}. '{flow_desc.name}' (ID: {flow_desc.id}) - Score: {score:.4f}")

if __name__ == "__main__":
    main()
