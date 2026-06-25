import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agentic_lca import LcaExecutor, FlowMapper

def search_improved(mapper, query, top_k=5):
    from collections import Counter
    import math

    candidate_pool_size = max(15, top_k * 3)

    # 1. Fast Dictionary Synonyms
    synonyms = mapper.synonyms
    query_lower = query.lower().strip()
    expanded_queries = []
    
    for abbr, full_name in synonyms.items():
        if abbr in query_lower:
            expanded_query = query_lower.replace(abbr, full_name)
            expanded_queries.append(expanded_query)
            
    # 2. Local LLM standard nomenclature expansion
    if mapper.llm_agent.is_ollama_active():
        try:
            llm_expanded = mapper.llm_agent.expand_material_query(query)
            for q in llm_expanded:
                if q.lower().strip() not in [eq.lower().strip() for eq in expanded_queries]:
                    expanded_queries.append(q)
        except Exception:
            pass
            
    # Include original query as fallback or primary search candidate (IMPORTANT!)
    if query not in expanded_queries:
        expanded_queries.append(query)
        
    combined_scores = {}
    for q in expanded_queries:
        query_tokens = mapper._tokenize(q)
        if not query_tokens:
            continue
            
        query_tf = Counter(query_tokens)
        query_tfidf = {}
        query_norm_sq = 0.0
        
        for token, freq in query_tf.items():
            tf_val = 1.0 + math.log(freq)
            df = mapper.doc_frequencies.get(token, 0)
            idf_val = math.log((1.0 + mapper.num_documents) / (1.0 + df)) + 1.0
            tfidf_val = tf_val * idf_val
            query_tfidf[token] = tfidf_val
            query_norm_sq += tfidf_val ** 2
            
        query_norm = math.sqrt(query_norm_sq) if query_norm_sq > 0 else 1.0
        
        q_scores = {}
        for token, q_val in query_tfidf.items():
            if token in mapper.inverted_index:
                for flow, doc_val in mapper.inverted_index[token]:
                    q_scores[flow.id] = q_scores.get(flow.id, 0.0) + (q_val * doc_val)
                    
        for flow_id, dot_product in q_scores.items():
            doc_norm = mapper.flow_norms.get(flow_id, 1.0)
            similarity = dot_product / (query_norm * doc_norm)
            combined_scores[flow_id] = max(combined_scores.get(flow_id, 0.0), similarity)
            
    results = []
    for flow_id, score in combined_scores.items():
        flow_desc = next((f for f in mapper.flows if f.id == flow_id), None)
        if flow_desc:
            results.append((flow_desc, score))
            
    results = sorted(results, key=lambda x: x[1], reverse=True)
    
    # Take the larger candidate pool
    pool = results[:candidate_pool_size]
    
    # Re-rank with LLM
    if len(pool) > 1 and mapper.llm_agent.is_ollama_active():
        try:
            print(f" -> Re-ranking {len(pool)} candidates for '{query}'...")
            pool = mapper.llm_agent.rerank_candidates(query, pool)
        except Exception as e:
            print(f" -> Re-ranking error: {e}")
            
    return pool[:top_k]

def main():
    executor = LcaExecutor()
    mapper = FlowMapper(executor)
    
    queries = ["PS", "solar silicon"]
    for q in queries:
        print(f"\n=== Improved Search for: '{q}' ===")
        results = search_improved(mapper, q, top_k=5)
        for idx, (flow_desc, score) in enumerate(results):
            print(f" {idx+1}. '{flow_desc.name}' (ID: {flow_desc.id}) - Score: {score:.4f}")

if __name__ == "__main__":
    main()
