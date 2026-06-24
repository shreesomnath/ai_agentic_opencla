import time
import math
from collections import Counter
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agentic_lca import LcaExecutor
import olca_schema as o

def main():
    executor = LcaExecutor()
    client = executor.client
    flows = list(client.get_descriptors(o.Flow))
    num_docs = len(flows)
    
    print(f"Loaded {num_docs} flows. Indexing with hybrid weights...")
    
    doc_freqs = Counter()
    temp_docs = []
    
    def tokenize(text):
        import re
        if not text: return []
        return [t for t in re.sub(r'[^\w\s\-\.]', ' ', text.lower()).split() if len(t) > 1]

    # First pass: doc frequencies
    for f in flows:
        name_toks = tokenize(f.name)
        cat_toks = tokenize(f.category)
        
        # Doc frequency counts set of tokens
        unique_tokens = set(name_toks) | set(cat_toks)
        for t in unique_tokens:
            doc_freqs[t] += 1
            
        temp_docs.append((f, name_toks, cat_toks))
        
    # Second pass: index building
    inverted_index = {}
    flow_norms = {}
    for f, name_toks, cat_toks in temp_docs:
        name_tf = Counter(name_toks)
        cat_tf = Counter(cat_toks)
        
        all_tokens = set(name_toks) | set(cat_toks)
        doc_norm_sq = 0.0
        
        for token in all_tokens:
            name_freq = name_tf.get(token, 0)
            cat_freq = cat_tf.get(token, 0)
            
            # Hybrid weight
            combined_freq = name_freq + 0.1 * cat_freq
            
            tf_val = 1.0 + math.log(combined_freq)
            df = doc_freqs.get(token, 0)
            idf_val = math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
            
            tfidf_val = tf_val * idf_val
            doc_norm_sq += tfidf_val ** 2
            
            if token not in inverted_index:
                inverted_index[token] = []
            inverted_index[token].append((f, tfidf_val))
            
        flow_norms[f.id] = math.sqrt(doc_norm_sq) if doc_norm_sq > 0 else 1.0

    # Search function
    def search(query):
        q_tokens = tokenize(query)
        q_tf = Counter(q_tokens)
        q_tfidf = {}
        q_norm_sq = 0.0
        for token, freq in q_tf.items():
            tf_val = 1.0 + math.log(freq)
            df = doc_freqs.get(token, 0)
            idf_val = math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
            tfidf_val = tf_val * idf_val
            q_tfidf[token] = tfidf_val
            q_norm_sq += tfidf_val ** 2
        q_norm = math.sqrt(q_norm_sq) if q_norm_sq > 0 else 1.0
        
        scores = {}
        for token, q_val in q_tfidf.items():
            if token in inverted_index:
                for f, doc_val in inverted_index[token]:
                    scores[f.id] = scores.get(f.id, 0.0) + (q_val * doc_val)
                    
        results = []
        for fid, dot in scores.items():
            similarity = dot / (q_norm * flow_norms[fid])
            f_desc = next(fd for fd in flows if fd.id == fid)
            results.append((f_desc, similarity))
        return sorted(results, key=lambda x: x[1], reverse=True)[:10]

    print("\nSearch results for 'polyethylene terephthalate' (Hybrid Weighting):")
    res = search("polyethylene terephthalate")
    for idx, (fd, score) in enumerate(res):
        print(f" {idx+1}. '{fd.name}' (Score: {score:.4f}, Category: {fd.category})")

if __name__ == "__main__":
    main()
