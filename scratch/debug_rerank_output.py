import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agentic_lca import LcaExecutor, FlowMapper

def main():
    executor = LcaExecutor()
    mapper = FlowMapper(executor)
    
    # We want to search for solar silicon
    query = "solar silicon"
    print(f"=== Debugging Re-ranking for '{query}' ===")
    
    # Get top 15 raw TF-IDF candidates first
    mapper.llm_agent.is_ollama_active = lambda: False
    raw_results = mapper.search(query, top_k=15)
    
    candidates_str = "\n".join([f"{idx+1}. Name: '{c[0].name}' (ID: {c[0].id}, Category: {c[0].category}, TF-IDF score: {c[1]:.4f})" for idx, c in enumerate(raw_results)])
    print(f"\nCandidates sent to LLM:\n{candidates_str}\n")
    
    # Run the LLM call directly
    prompt = f"""
You are an expert material database matching engine for life cycle assessment (LCA).
The user is looking for a flow in the ecoinvent database that matches their feedstock: "{query}"

Here are the top candidates retrieved from the database using a text keyword search:
{candidates_str}

Evaluate these candidates based on:
1. Physical/chemical composition: Does the chemical substance or material class match?
2. Recycled/circular status: If the query specifies "recycled", "scrap", "secondary", "reclaimed", or "cullet", prioritize candidates that contain these words or represent secondary recycling processes. Do NOT choose virgin materials if recycled/scrap alternatives are available in the list.
3. Class precision.

Identify the best order of matches. Return a JSON array of integers representing the 1-based indices of the candidates in order of preference (best match first, e.g. [2, 1, 3, 4, 5]). 
Output only the JSON array and nothing else.
"""
    mapper.llm_agent.is_ollama_active = lambda: True
    response = mapper.llm_agent._call_llm(prompt, json_format=True)
    print(f"LLM Response: {response}")

if __name__ == "__main__":
    main()
