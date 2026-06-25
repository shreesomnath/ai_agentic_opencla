import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agentic_lca import LcaExecutor, FlowMapper

def main():
    executor = LcaExecutor()
    mapper = FlowMapper(executor)
    
    # Run searches without LLM to isolate TF-IDF + Synonym logic
    mapper.llm_agent.is_ollama_active = lambda: False
    
    for q in ["PS", "polystyrene"]:
        print(f"\n=== Search results for: '{q}' ===")
        results = mapper.search(q, top_k=10)
        for idx, (flow_desc, score) in enumerate(results):
            print(f" {idx+1}. '{flow_desc.name}' (ID: {flow_desc.id}) - Score: {score:.4f}")

if __name__ == "__main__":
    main()
