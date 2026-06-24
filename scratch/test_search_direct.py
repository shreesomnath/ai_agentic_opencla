import time
from agentic_lca import LcaExecutor, FlowMapper

def main():
    executor = LcaExecutor()
    mapper = FlowMapper(executor)
    
    q = "polyethylene terephthalate"
    print(f"Direct search for '{q}':")
    
    # Let's bypass LLM re-ranking to see raw TF-IDF scores
    # We temporarily set mapper.llm_agent.is_ollama_active to lambda: False
    orig_is_active = mapper.llm_agent.is_ollama_active
    mapper.llm_agent.is_ollama_active = lambda: False
    
    results = mapper.search(q, top_k=20)
    for idx, (flow_desc, score) in enumerate(results):
        print(f" {idx+1}. '{flow_desc.name}' (Score: {score:.4f}, Category: {flow_desc.category})")
        
    mapper.llm_agent.is_ollama_active = orig_is_active
    
if __name__ == "__main__":
    main()
