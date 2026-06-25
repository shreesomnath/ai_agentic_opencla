import math

class TopsisDecisionEngine:
    """
    Implements the Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS)
    for multi-criteria sustainability decision support.
    """
    @staticmethod
    def rank_alternatives(alternatives, weights):
        """
        Ranks a list of alternatives based on criteria values using TOPSIS.
        All criteria (GWP, Acidification, Water, Cost) are assumed to be minimization objectives.
        
        Parameters:
          alternatives: List of dicts, where each dict has:
            - 'index' or ID identifier
            - 'metrics': Dict with keys matching weights keys (e.g., {'GWP': val, 'Cost': val, ...})
          weights: Dict mapping metric names to priority weights (must sum to > 0)
          
        Returns:
          A list of alternatives with a 'topsis_score' and 'rank' added, sorted by score in descending order.
        """
        if not alternatives:
            return []
            
        # 1. Normalize weights
        total_w = sum(weights.values())
        if total_w == 0:
            # Equal weights fallback
            norm_weights = {k: 1.0 / len(weights) for k in weights.keys()}
        else:
            norm_weights = {k: w / total_w for k, w in weights.items()}
            
        keys = list(norm_weights.keys())
        m = len(alternatives)
        n = len(keys)
        
        # 2. Construct decision matrix
        matrix = []
        for alt in alternatives:
            row = []
            for k in keys:
                row.append(float(alt["metrics"].get(k, 0.0)))
            matrix.append(row)
            
        # 3. Calculate sum of squares for normalization denominators
        denominators = [0.0] * n
        for j in range(n):
            sq_sum = sum(matrix[i][j] ** 2 for i in range(m))
            denominators[j] = math.sqrt(sq_sum) if sq_sum > 0 else 1.0
            
        # 4. Normalize and weight decision matrix
        weighted_matrix = []
        for i in range(m):
            row = []
            for j in range(n):
                # Normalized value
                norm_val = matrix[i][j] / denominators[j]
                # Weighted normalized value
                weighted_val = norm_val * norm_weights[keys[j]]
                row.append(weighted_val)
            weighted_matrix.append(row)
            
        # 5. Determine ideal best (A*) and ideal worst (A-) solutions
        # Since all criteria are MINIMIZATION, ideal best is the minimum, worst is the maximum
        ideal_best = []
        ideal_worst = []
        for j in range(n):
            col_vals = [weighted_matrix[i][j] for i in range(m)]
            ideal_best.append(min(col_vals))
            ideal_worst.append(max(col_vals))
            
        # 6. Calculate Euclidean distances and closeness coefficient
        ranked_results = []
        for i in range(m):
            dist_best = math.sqrt(sum((weighted_matrix[i][j] - ideal_best[j]) ** 2 for j in range(n)))
            dist_worst = math.sqrt(sum((weighted_matrix[i][j] - ideal_worst[j]) ** 2 for j in range(n)))
            
            # Relative closeness
            denom = dist_best + dist_worst
            score = dist_worst / denom if denom > 0 else 0.5
            
            # Copy alternative and inject score
            alt_copy = dict(alternatives[i])
            alt_copy["topsis_score"] = score
            ranked_results.append(alt_copy)
            
        # 7. Sort by score descending and assign rank
        ranked_results = sorted(ranked_results, key=lambda x: x["topsis_score"], reverse=True)
        for rank_idx, alt in enumerate(ranked_results):
            alt["topsis_rank"] = rank_idx + 1
            
        return ranked_results
