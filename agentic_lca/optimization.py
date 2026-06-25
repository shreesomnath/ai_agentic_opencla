import random
import olca_schema as o

class ParetoOptimizer:
    """
    Executes multi-objective feedstock blending optimization using linear sensitivity
    surrogate models to find the Pareto-optimal frontier across multiple indicators.
    """
    def __init__(self, executor, mapper, verifier, cost_registry=None):
        self.executor = executor
        self.client = executor.client
        self.mapper = mapper
        self.verifier = verifier
        from .multiobjective import CostRegistry
        self.cost_registry = cost_registry if cost_registry else CostRegistry()

    def optimize_process(self, process_id, system_id, method_id, num_samples=2000):
        """
        Builds a linear surrogate model for all feedstock substitutions and returns the Pareto frontier.
        """
        proc = self.client.get(o.Process, process_id)
        
        # 1. Identify input exchanges that represent physical material feedstocks
        input_exchanges = []
        for e in proc.exchanges:
            if not (e.is_input and e.flow and e.amount > 0):
                continue
            unit_name = (e.unit.name or "").lower() if e.unit else ""
            flow_name = (e.flow.name or "").lower()
            
            # Keep only mass-based physical feedstocks
            if unit_name not in ["kg", "g", "t", "ton", "kg(active substance)"]:
                continue
            # Exclude services, transport, energy, and water
            if any(term in flow_name for term in ["electricity", "transport", "freight", "lorry", "air", "water", "heat", "steam", "transmission", "distribution"]):
                continue
            input_exchanges.append(e)
        
        # 2. For each feedstock, find its recycled/secondary substitute flow descriptor
        substitutes = {}
        for ex in input_exchanges:
            flow_name = ex.flow.name
            flow_id = ex.flow.id
            
            flow_lower = flow_name.lower()
            if "recycled" in flow_lower or "cullet" in flow_lower or "scrap" in flow_lower:
                continue # Already recycled
                
            # Search query
            if "glass" in flow_lower:
                search_query = "glass cullet sorted"
            elif "steel" in flow_lower:
                search_query = "scrap steel"
            elif "polyethylene" in flow_lower or "plastic" in flow_lower:
                search_query = "polyethylene recycled"
            else:
                search_query = f"{flow_name.split(',')[0]} recycled"
                
            matches = self.mapper.search(search_query, top_k=5)
            sub_desc = None
            for fd, score in matches:
                if fd.id != flow_id:
                    if "recycled" in fd.name.lower() or "cullet" in fd.name.lower() or "scrap" in fd.name.lower():
                        sub_desc = fd
                        break
            if not sub_desc and matches:
                sub_desc = next((f for f, s in matches if f.id != flow_id), None)
                
            if sub_desc:
                substitutes[flow_id] = sub_desc
                print(f"[Pareto] Found substitute for '{flow_name}': '{sub_desc.name}'")

        if not substitutes:
            print("[Pareto Warning] No substitutable feedstocks identified.")
            return []

        # 3. Calculate baseline metrics
        baseline_results = self.executor.calculate(system_id, method_id)
        
        target_categories = {
            "GWP": ["global warming", "climate change", "gwp", "greenhouse", "carbon footprint"],
            "Acidification": ["acidification", "ap", "acidifying potential"],
            "Water": ["water consumption", "water use", "water scarcity", "water depletion", "freshwater consumption"]
        }
        
        baselines = {}
        category_full_names = {}
        
        for kpi, queries in target_categories.items():
            found = next((item for item in baseline_results if any(q in item["category_name"].lower() for q in queries)), None)
            if found:
                baselines[kpi] = found["amount"]
                category_full_names[kpi] = found["category_name"]
            else:
                baselines[kpi] = 0.0
                category_full_names[kpi] = kpi
                
        # Baseline Cost
        total_cost_baseline = 0.0
        for exchange in proc.exchanges:
            if exchange.is_input and exchange.flow:
                total_cost_baseline += self.cost_registry.get_flow_cost(exchange.flow.name, exchange.amount, exchange.unit.name if exchange.unit else "")
        baselines["Cost"] = total_cost_baseline

        # 4. Calculate marginal impacts for both virgin and recycled options
        delta_impacts = {}
        
        for flow_id, sub_desc in substitutes.items():
            exchange = next(e for e in input_exchanges if e.flow.id == flow_id)
            orig_flow_ref = exchange.flow
            amount = exchange.amount
            
            substitute_ref = o.Ref(
                ref_type=o.RefType.Flow,
                id=sub_desc.id,
                name=sub_desc.name,
                ref_unit=sub_desc.ref_unit
            )
            
            # Apply substitution temporarily in DB
            exchange.flow = substitute_ref
            self.client.put(proc)
            
            # Re-compile temporary product system to evaluate actual footprint
            sys_obj = self.client.get(o.ProductSystem, system_id)
            temp_sys = self.client.create_product_system(sys_obj.ref_process)
            
            delta_impacts[flow_id] = {}
            
            try:
                opt_results = self.executor.calculate(temp_sys.id, method_id)
                for kpi, queries in target_categories.items():
                    opt_item = next((r for r in opt_results if r["category_name"] == category_full_names[kpi]), None)
                    if not opt_item:
                        opt_item = next((r for r in opt_results if any(q in r["category_name"].lower() for q in queries)), None)
                    opt_val = opt_item["amount"] if opt_item else baselines[kpi]
                    
                    delta_impacts[flow_id][kpi] = opt_val - baselines[kpi]
            except Exception as e:
                print(f"[Pareto] Error calculating footprint of substitute '{sub_desc.name}': {e}")
                for kpi in target_categories.keys():
                    delta_impacts[flow_id][kpi] = 0.0
            finally:
                # Cleanup temporary product system
                try: self.client.delete(o.Ref(ref_type=o.RefType.ProductSystem, id=temp_sys.id))
                except: pass
                # Restore baseline exchange
                exchange.flow = orig_flow_ref
                self.client.put(proc)

            # Cost change for 100% swap
            unit_name = exchange.unit.name if exchange.unit else ""
            virgin_cost = self.cost_registry.get_flow_cost(orig_flow_ref.name, amount, unit_name)
            recycled_cost = self.cost_registry.get_flow_cost(sub_desc.name, amount, unit_name)
            delta_impacts[flow_id]["Cost"] = recycled_cost - virgin_cost

        # 5. Advanced Genetic Algorithm (NSGA-II) Optimization Search
        # Define bounds: ratio for each substitutes [0.0, 1.0], efficiency [0.8, 1.2], loss [0.0, 0.2]
        bounds = [(0.0, 1.0)] * len(substitutes) + [(0.8, 1.2), (0.0, 0.2)]
        num_vars = len(bounds)
        
        def chromosome_to_point(chrom):
            ratios_named = {}
            for idx, flow_id in enumerate(substitutes.keys()):
                flow_name = next(e.flow.name for e in input_exchanges if e.flow.id == flow_id)
                ratios_named[flow_name] = chrom[idx]
                
            sampled_eff = chrom[num_vars - 2]
            sampled_loss = chrom[num_vars - 1]
            scale = (1.0 + sampled_loss) / sampled_eff
            
            pt_metrics = {}
            for kpi in baselines.keys():
                val = baselines[kpi]
                for idx, flow_id in enumerate(substitutes.keys()):
                    r = chrom[idx]
                    val += r * delta_impacts[flow_id].get(kpi, 0.0)
                pt_metrics[kpi] = val * scale
                
            return {
                "ratios": ratios_named,
                "parameters": {
                    "process_efficiency": sampled_eff,
                    "loss_factor": sampled_loss
                },
                "metrics": pt_metrics,
                "chromosome": chrom
            }

        # Parent tournament selector
        def binary_tournament(pop, fronts, crowding_dists):
            ranks = {}
            for rank_idx, front in enumerate(fronts):
                for p in front:
                    ranks[p] = rank_idx
                    
            p1_idx = random.randint(0, len(pop) - 1)
            p2_idx = random.randint(0, len(pop) - 1)
            
            r1 = ranks.get(p1_idx, 9999)
            r2 = ranks.get(p2_idx, 9999)
            
            if r1 < r2:
                return pop[p1_idx]
            elif r2 < r1:
                return pop[p2_idx]
            else:
                cd1 = crowding_dists.get(p1_idx, -1.0)
                cd2 = crowding_dists.get(p2_idx, -1.0)
                return pop[p1_idx] if cd1 > cd2 else pop[p2_idx]

        # Initialize GA population
        pop_size = 150
        generations = 60
        population = []
        for _ in range(pop_size):
            chrom = [random.uniform(low, high) for (low, high) in bounds]
            population.append(chromosome_to_point(chrom))
            
        for gen in range(generations):
            # Create offspring via crossover & mutation
            offspring = []
            fronts = fast_non_dominated_sort(population)
            crowding_dists = {}
            for front in fronts:
                dists = calculate_crowding_distance(front, population)
                for idx, d in dists.items():
                    crowding_dists[idx] = d
                    
            while len(offspring) < pop_size:
                p1 = binary_tournament(population, fronts, crowding_dists)
                p2 = binary_tournament(population, fronts, crowding_dists)
                
                # Blend Crossover (BLX-alpha)
                c1_chrom, c2_chrom = [], []
                for g1, g2, (low, high) in zip(p1["chromosome"], p2["chromosome"], bounds):
                    alpha = 0.15
                    min_g, max_g = min(g1, g2), max(g1, g2)
                    diff = max_g - min_g
                    c_low = max(low, min_g - alpha * diff)
                    c_high = min(high, max_g + alpha * diff)
                    c1_chrom.append(random.uniform(c_low, c_high))
                    c2_chrom.append(random.uniform(c_low, c_high))
                    
                # Mutation: slight perturbations
                for c_chrom in [c1_chrom, c2_chrom]:
                    for idx in range(num_vars):
                        if random.random() < 0.25:
                            low, high = bounds[idx]
                            delta = random.normalvariate(0, 0.12 * (high - low))
                            c_chrom[idx] = max(low, min(high, c_chrom[idx] + delta))
                            
                offspring.append(chromosome_to_point(c1_chrom))
                offspring.append(chromosome_to_point(c2_chrom))
                
            # Truncation selection: elitism merge
            combined = population + offspring[:pop_size]
            combined_fronts = fast_non_dominated_sort(combined)
            next_pop = []
            
            for front in combined_fronts:
                front_dists = calculate_crowding_distance(front, combined)
                if len(next_pop) + len(front) <= pop_size:
                    for idx in front:
                        next_pop.append(combined[idx])
                else:
                    sorted_front = sorted(front, key=lambda idx: front_dists.get(idx, 0.0), reverse=True)
                    for idx in sorted_front[:pop_size - len(next_pop)]:
                        next_pop.append(combined[idx])
                    break
            population = next_pop
            
        # Extract Pareto frontier of final population
        final_fronts = fast_non_dominated_sort(population)
        frontier = [population[idx] for idx in final_fronts[0]]
        print(f"[Pareto-GA] Evolved {generations} generations (pop={pop_size}). Identified {len(frontier)} absolute optimal frontier boundary points.")
        return frontier

def fast_non_dominated_sort(population):
    S = [[] for _ in range(len(population))]
    n = [0] * len(population)
    rank = [0] * len(population)
    fronts = [[]]
    
    for p in range(len(population)):
        for q in range(len(population)):
            p_metrics = population[p]["metrics"]
            q_metrics = population[q]["metrics"]
            
            p_dominates_q = (
                p_metrics["GWP"] <= q_metrics["GWP"] and
                p_metrics["Acidification"] <= q_metrics["Acidification"] and
                p_metrics["Water"] <= q_metrics["Water"] and
                p_metrics["Cost"] <= q_metrics["Cost"] and
                (p_metrics["GWP"] < q_metrics["GWP"] or
                 p_metrics["Acidification"] < q_metrics["Acidification"] or
                 p_metrics["Water"] < q_metrics["Water"] or
                 p_metrics["Cost"] < q_metrics["Cost"])
            )
            
            q_dominates_p = (
                q_metrics["GWP"] <= p_metrics["GWP"] and
                q_metrics["Acidification"] <= p_metrics["Acidification"] and
                q_metrics["Water"] <= p_metrics["Water"] and
                q_metrics["Cost"] <= p_metrics["Cost"] and
                (q_metrics["GWP"] < p_metrics["GWP"] or
                 q_metrics["Acidification"] < p_metrics["Acidification"] or
                 q_metrics["Water"] < p_metrics["Water"] or
                 q_metrics["Cost"] < p_metrics["Cost"])
            )
            
            if p_dominates_q:
                S[p].append(q)
            elif q_dominates_p:
                n[p] += 1
                
        if n[p] == 0:
            rank[p] = 0
            fronts[0].append(p)
            
    i = 0
    while len(fronts[i]) > 0:
        next_front = []
        for p in fronts[i]:
            for q in S[p]:
                n[q] -= 1
                if n[q] == 0:
                    rank[q] = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)
        
    return fronts[:-1]

def calculate_crowding_distance(front, population):
    if len(front) == 0:
        return {}
        
    distances = {p: 0.0 for p in front}
    objectives = ["GWP", "Acidification", "Water", "Cost"]
    
    for obj in objectives:
        sorted_front = sorted(front, key=lambda p: population[p]["metrics"][obj])
        
        # Boundary elements
        distances[sorted_front[0]] = float('inf')
        distances[sorted_front[-1]] = float('inf')
        
        min_val = population[sorted_front[0]]["metrics"][obj]
        max_val = population[sorted_front[-1]]["metrics"][obj]
        diff = max_val - min_val
        
        if diff == 0:
            continue
            
        for i in range(1, len(sorted_front) - 1):
            distances[sorted_front[i]] += (
                population[sorted_front[i+1]]["metrics"][obj] - 
                population[sorted_front[i-1]]["metrics"][obj]
            ) / diff
            
    return distances

def get_pareto_frontier(points):
    pareto_frontier = []
    for i, p1 in enumerate(points):
        dominated = False
        y1 = p1["metrics"]
        
        for j, p2 in enumerate(points):
            if i == j:
                continue
            y2 = p2["metrics"]
            
            if (y2["GWP"] <= y1["GWP"] and 
                y2["Acidification"] <= y1["Acidification"] and 
                y2["Water"] <= y1["Water"] and 
                y2["Cost"] <= y1["Cost"] and 
                (y2["GWP"] < y1["GWP"] or 
                 y2["Acidification"] < y1["Acidification"] or 
                 y2["Water"] < y1["Water"] or 
                 y2["Cost"] < y1["Cost"])):
                dominated = True
                break
                
        if not dominated:
            pareto_frontier.append(p1)
            
    return pareto_frontier
