import math
import re
from collections import Counter
import olca_schema as o

class FlowMapper:
    """
    Performs local semantic mapping between unstructured user inventories and 
    structured LCA database flows using a pure-Python TF-IDF index.
    No API keys or heavy deep-learning dependencies are required.
    """
    def __init__(self, executor):
        self.executor = executor
        self.client = executor.client
        self.flows = []
        self.doc_frequencies = Counter()
        self.num_documents = 0
        self.inverted_index = {}
        self.flow_norms = {}
        self.indexed_flows = []
        
        self._load_and_index_flows()

    def _tokenize(self, text):
        """Tokenizes text and filters out short words."""
        if not text:
            return []
        # Lowercase, replace punctuation with spaces, and split
        text_clean = re.sub(r'[^\w\s\-\.]', ' ', text.lower())
        tokens = text_clean.split()
        return [t for t in tokens if len(t) > 1]

    def _load_and_index_flows(self):
        """Retrieves and indexes all flows in the openLCA database."""
        print("Retrieving flows from openLCA database (this might take a few seconds)...")
        self.flows = list(self.client.get_descriptors(o.Flow))
        self.num_documents = len(self.flows)
        print(f"Loaded {self.num_documents} flows. Building TF-IDF index...")
        
        # 1. First pass: count document frequencies for IDF
        temp_docs = []
        for idx, flow in enumerate(self.flows):
            tokens = self._tokenize(flow.name)
            # Incorporate category strings to improve contextual matching
            if flow.category:
                category_tokens = self._tokenize(flow.category)
                tokens.extend(category_tokens)
                
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_frequencies[t] += 1
            temp_docs.append((flow, tokens))
            
        # 2. Second pass: build inverted index and doc tf-idf norms
        for flow, tokens in temp_docs:
            tf = Counter(tokens)
            doc_tfidf = {}
            doc_norm_sq = 0.0
            
            for token, freq in tf.items():
                # TF: term frequency log scaling
                tf_val = 1.0 + math.log(freq)
                # IDF: document frequency scaling
                df = self.doc_frequencies.get(token, 0)
                idf_val = math.log((1.0 + self.num_documents) / (1.0 + df)) + 1.0
                
                tfidf_val = tf_val * idf_val
                doc_tfidf[token] = tfidf_val
                doc_norm_sq += tfidf_val ** 2
                
                if token not in self.inverted_index:
                    self.inverted_index[token] = []
                self.inverted_index[token].append((flow, tfidf_val))
                
            self.flow_norms[flow.id] = math.sqrt(doc_norm_sq) if doc_norm_sq > 0 else 1.0
            self.indexed_flows.append(flow)
            
        print("TF-IDF mapping index built successfully!")

    def search(self, query, top_k=5, flow_type_filter=None):
        """
        Searches the indexed database flows using cosine similarity.
        Optionally filters results by o.FlowType.
        Returns a list of tuples: (flow_descriptor, similarity_score)
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
            
        query_tf = Counter(query_tokens)
        query_tfidf = {}
        query_norm_sq = 0.0
        
        # Calculate query TF-IDF vector
        for token, freq in query_tf.items():
            tf_val = 1.0 + math.log(freq)
            df = self.doc_frequencies.get(token, 0)
            idf_val = math.log((1.0 + self.num_documents) / (1.0 + df)) + 1.0
            tfidf_val = tf_val * idf_val
            query_tfidf[token] = tfidf_val
            query_norm_sq += tfidf_val ** 2
            
        query_norm = math.sqrt(query_norm_sq) if query_norm_sq > 0 else 1.0
        
        # Calculate dot products with matching documents
        scores = {}
        for token, q_val in query_tfidf.items():
            if token in self.inverted_index:
                for flow, doc_val in self.inverted_index[token]:
                    scores[flow.id] = scores.get(flow.id, 0.0) + (q_val * doc_val)
                    
        # Divide by norms to get cosine similarity
        results = []
        for flow_id, dot_product in scores.items():
            doc_norm = self.flow_norms.get(flow_id, 1.0)
            similarity = dot_product / (query_norm * doc_norm)
            
            # Retrieve descriptor
            flow_desc = next((f for f in self.flows if f.id == flow_id), None)
            if flow_desc:
                # Apply flow type filter if specified
                if flow_type_filter:
                    ft = getattr(flow_desc, "flow_type", None)
                    if ft:
                        ft_name = ft.name if hasattr(ft, "name") else str(ft)
                        filter_name = flow_type_filter.name if hasattr(flow_type_filter, "name") else str(flow_type_filter)
                        if ft_name != filter_name:
                            continue
                results.append((flow_desc, similarity))
                
        # Sort results by similarity score
        results = sorted(results, key=lambda x: x[1], reverse=True)
        return results[:top_k]
