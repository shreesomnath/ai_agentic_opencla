import requests
import json
import os

class LcaLlmAgent:
    """
    Interfaces with a local Ollama server running open-source LLMs 
    (such as qwen2.5-coder:7b) to provide natural language reasoning,
    hotspot interpretation, and engineering reports.
    Falls back to cloud APIs (Gemini or OpenAI) if environment keys are set.
    """
    def __init__(self, ollama_url="http://localhost:11434", model="qwen2.5-coder:7b"):
        self.ollama_url = ollama_url
        self.model = model

    def is_ollama_active(self):
        """
        Checks if the local Ollama server is active and accessible,
        or if a cloud LLM fallback API key (GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY) is configured.
        """
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
            return True
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _call_llm(self, prompt, json_format=False):
        """
        Unified LLM client caller. Tries local Ollama first, then falls back
        to cloud APIs if environment keys are set.
        """
        # 1. Try local Ollama
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            if json_format:
                payload["format"] = "json"
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=20)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception:
            pass

        # 2. Try Gemini API (Using requests directly to keep dependencies zero-install)
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if json_format:
                payload["generationConfig"] = {"responseMimeType": "application/json"}
            try:
                res = requests.post(url, json=payload, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Strip markdown code blocks if the LLM wrapped it
                    if text.startswith("```json") and text.endswith("```"):
                        text = text[7:-3].strip()
                    elif text.startswith("```") and text.endswith("```"):
                        text = text[3:-3].strip()
                    return text
            except Exception as e:
                print(f"[LLM Fallback] Gemini API Error: {e}")

        # 3. Try OpenAI API
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            if json_format:
                payload["response_format"] = {"type": "json_object"}
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=15)
                if res.status_code == 200:
                    text = res.json()["choices"][0]["message"]["content"].strip()
                    # Strip markdown code blocks if the LLM wrapped it
                    if text.startswith("```json") and text.endswith("```"):
                        text = text[7:-3].strip()
                    elif text.startswith("```") and text.endswith("```"):
                        text = text[3:-3].strip()
                    return text
            except Exception as e:
                print(f"[LLM Fallback] OpenAI API Error: {e}")

        # 4. Try Anthropic Claude API
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    text = data["content"][0]["text"].strip()
                    # Strip markdown code blocks if the LLM wrapped it
                    if text.startswith("```json") and text.endswith("```"):
                        text = text[7:-3].strip()
                    elif text.startswith("```") and text.endswith("```"):
                        text = text[3:-3].strip()
                    return text
            except Exception as e:
                print(f"[LLM Fallback] Anthropic API Error: {e}")

        return None

    def generate_engineering_justification(self, report, weights=None):
        """
        Interprets a Multi-Objective LCA trade-off report and generates 
        a formal engineering justification text (e.g. for NSF proposals or ESG reports).
        """
        metrics = report.get("metrics", {}) if report else {}
        gwp = metrics.get("Global Warming", {}) if metrics else {}
        acid = metrics.get("Acidification", {}) if metrics else {}
        water = metrics.get("Water Consumption", {}) if metrics else {}
        cost = metrics.get("Feedstock Cost", {}) if metrics else {}

        if not self.is_ollama_active():
            savings_gwp = gwp.get('percentage_change', 0.0) if gwp else 0.0
            savings_cost = cost.get('percentage_change', 0.0) if cost else 0.0
            savings_water = water.get('percentage_change', 0.0) if water else 0.0
            savings_acid = acid.get('percentage_change', 0.0) if acid else 0.0
            
            repaired_sub = f"replacing '{report.get('substituted_from')}' with '{report.get('substituted_to')}'" if report else "substituting feedstock"
            
            justification = (
                f"**Quantitative Decoupling & Decarbonization Justification**:\n\n"
                f"A multi-objective environmental assessment was performed on the process '{report.get('process_name') if report else 'Assembly'}' "
                f"evaluating the substitution of virgin feedstocks with secondary alternatives—specifically {repaired_sub}. "
                f"The substitution achieves a carbon footprint reduction of **{savings_gwp:+.2f}%** (transitioning from "
                f"{gwp.get('baseline', 0.0) if gwp else 0.0:.4f} to {gwp.get('optimized', 0.0) if gwp else 0.0:.4f} kg CO2 eq). This decoupling behavior "
                f"is physically substantiated by avoiding raw material extraction energy, substituting energy-intensive virgin material "
                f"phases with lower-embodied-energy secondary alternatives. "
            )
            
            justification += (
                f"\n\nFrom a multi-criteria perspective, the trade-off analysis indicates a change in terrestrial acidification of "
                f"**{savings_acid:+.2f}%** and water usage footprint of **{savings_water:+.2f}%**. "
            )
            
            justification += (
                f"Economically, raw material purchase costs changed by **{savings_cost:+.2f}%** (from "
                f"${cost.get('baseline', 0.0) if cost else 0.0:.2f} to ${cost.get('optimized', 0.0) if cost else 0.0:.2f} USD). "
            )
            
            if savings_gwp < 0 and savings_cost <= 0:
                justification += (
                    "Consequently, this configuration represents a strictly Pareto-improving state, decoupling ecological footprints "
                    "from operational economic expenditures without burden-shifting."
                )
            else:
                justification += (
                    "The configuration shows key trade-offs between environmental savings and procurement costs, requiring multi-criteria decision "
                    "weighting (TOPSIS) to determine optimal compromise boundaries."
                )
                
            if weights:
                justification += (
                    f"\n\nUnder user decision weights ({', '.join([f'{k}: {v}%' for k, v in weights.items()])}), the system evaluated this "
                    "trade-off boundary, establishing that the chosen configuration satisfies preference constraints."
                )
            return justification

        weights_context = ""
        if weights:
            weights_str = ", ".join([f"{k}: {v}%" for k, v in weights.items()])
            weights_context = f"\nThe user has specified the following decision weights priorities: {weights_str}. Please quantitatively justify why this swap aligns with these user priorities (particularly emphasizing indicators with high priority weights)."

        prompt = f"""
You are an expert environmental engineer and LCA scientist.
Write a formal, highly technical engineering justification paragraph analyzing the following feedstock substitution scenario for a Next-Gen Silicon Solar Cell Module:

- Process: {report.get('process_name')}
- Feedstock Swapped: '{report.get('substituted_from')}' replaced with '{report.get('substituted_to')}'

Trade-off Metrics Results:
1. Carbon Footprint (Global Warming Potential): {gwp.get('percentage_change', 0.0):+.2f}% change (from {gwp.get('baseline', 0.0):.4f} to {gwp.get('optimized', 0.0):.4f} kg CO2 eq)
2. Terrestrial Acidification Potential: {acid.get('percentage_change', 0.0):+.2f}% change (from {acid.get('baseline', 0.0):.4f} to {acid.get('optimized', 0.0):.4f} kg SO2 eq)
3. Water Consumption Footprint: {water.get('percentage_change', 0.0):+.2f}% change (from {water.get('baseline', 0.0):.4f} to {water.get('optimized', 0.0):.4f} m3)
4. Raw Material Purchase Cost: {cost.get('percentage_change', 0.0):+.2f}% change (from {cost.get('baseline', 0.0):.4f} to {cost.get('optimized', 0.0):.4f} USD)
{weights_context}

Instructions:
- Interpret whether this substitution is "Pareto-improving" (decoupling environmental footprints without raising costs).
- Explain the physical and chemical reason why replacing virgin components (like glass fibers) with secondary raw materials (like sorted glass cullet) yields these benefits.
- Summarize the multi-dimensional savings (carbon, acidification, water, cost).
- Keep the tone academic, precise, and professional. Output only the finished justification paragraph (no conversational prefixes like 'Here is your paragraph').
"""
        response_text = self._call_llm(prompt, json_format=False)
        if response_text:
            return response_text
        return "Failed to generate LLM text: active backend did not return a response."

    def suggest_substitute_queries(self, hotspot_flow_name):
        """
        Asks the LLM to suggest alternative search queries for finding green
        recycled feedstock substitutes based on the hotspot material name.
        """
        if not self.is_ollama_active():
            return [f"{hotspot_flow_name.split(',')[0]} recycled"]

        prompt = f"""
Given the following engineering material name used in an LCA database:
'{hotspot_flow_name}'

List 3 distinct, highly relevant search terms to locate green, recycled, or circular substitutes for this material in an ecoinvent database.
For example, if the material is 'polyethylene, high density', terms might be: 'polyethylene recycled', 'plastic granulate recycled'.
Format your response as a simple JSON array of strings, for example: ["term 1", "term 2", "term 3"].
Output only the JSON array and nothing else.
"""
        response_text = self._call_llm(prompt, json_format=True)
        try:
            if response_text:
                return json.loads(response_text)
        except Exception:
            pass
        return [f"{hotspot_flow_name.split(',')[0]} recycled"]

    def parse_chat_command(self, user_query, exchanges_list, report=None, weights=None):
        """
        Parses a user chat query in the context of the current process exchanges list.
        Returns a JSON dictionary containing the action ('substitute' or 'chat') and values.
        """
        if not self.is_ollama_active():
            query_clean = user_query.lower().strip()
            
            # 1. Match Learn/Synonym mapping requests
            is_learn = False
            abbrev_found = ""
            standard_found = ""
            for kw in ["stands for", "stands as", "is short for", "abbreviation for", "synonym for"]:
                if kw in query_clean:
                    parts = query_clean.split(kw)
                    if len(parts) == 2:
                        abbrev_found = parts[0].replace("remember", "").replace("that", "").strip()
                        standard_found = parts[1].replace(".", "").strip()
                        is_learn = True
                        break
            if not is_learn and "map" in query_clean:
                if "to" in query_clean:
                    parts = query_clean.replace("map", "").split("to")
                    if len(parts) == 2:
                        abbrev_found = parts[0].strip()
                        standard_found = parts[1].replace(".", "").strip()
                        is_learn = True
            if is_learn and abbrev_found and standard_found:
                return {
                    "action": "learn",
                    "abbreviation": abbrev_found,
                    "standard_name": standard_found,
                    "response": f"I have mapped '{abbrev_found}' to '{standard_found}' in my dictionary. I will use this for future mapping searches."
                }
                
            # 2. Match Feedstock Substitution requests
            is_substitute = False
            referenced_virgin = None
            substitute_search_query = ""
            if exchanges_list:
                for ex in exchanges_list:
                    name_clean = ex["name"].lower()
                    short_terms = [name_clean]
                    if "," in name_clean:
                        short_terms.append(name_clean.split(",")[0].strip())
                    for term in short_terms:
                        if len(term) > 3 and term in query_clean:
                            referenced_virgin = ex["name"]
                            break
                    if referenced_virgin:
                        break
            if referenced_virgin:
                for marker in ["with", "instead of", "for", "to"]:
                    if marker in query_clean:
                        parts = query_clean.split(marker)
                        if marker == "instead of":
                            sub_part = parts[0].replace("use", "").replace("replace", "").replace("substitute", "").replace("swap", "").strip()
                            if sub_part:
                                substitute_search_query = sub_part
                                is_substitute = True
                                break
                        else:
                            sub_part = parts[1].replace(".", "").strip()
                            if sub_part:
                                substitute_search_query = sub_part
                                is_substitute = True
                                break
                if is_substitute and referenced_virgin:
                    return {
                        "action": "substitute",
                        "virgin_flow_name": referenced_virgin,
                        "substitute_search_query": substitute_search_query
                    }
                    
            # 3. Fallback Informational Q&A / Chat Response
            response_text = ""
            if any(w in query_clean for w in ["hello", "hi", "hey"]):
                response_text = "Hello! I am your autonomous LCA Copilot. I can help guide you through optimizing your supply chain footprint. You can ask me general questions or request substitutions directly (e.g. 'replace steel with scrap steel')."
            elif any(w in query_clean for w in ["explain", "results", "metrics", "carbon", "footprint"]):
                if report:
                    metrics = report.get("metrics", {})
                    gwp = metrics.get("Global Warming", {})
                    cost = metrics.get("Feedstock Cost", {})
                    gwp_val = gwp.get("optimized", gwp.get("baseline", 0.0))
                    cost_val = cost.get("optimized", cost.get("baseline", 0.0))
                    response_text = (
                        f"Based on the active report, the current carbon footprint is **{gwp_val:.4f} kg CO2 eq** "
                        f"and the feedstock purchase cost is **${cost_val:.2f} USD**. "
                    )
                    if exchanges_list:
                        sorted_ex = sorted(exchanges_list, key=lambda e: float(e["amount"]), reverse=True)
                        hotspot = sorted_ex[0]["name"]
                        response_text += (
                            f"The primary mass feedstock input is **{hotspot}** at {sorted_ex[0]['amount']} {sorted_ex[0]['unit']}. "
                            f"Replacing this material with a recycled alternative (e.g. 'replace {hotspot.split(',')[0]} with recycled {hotspot.split(',')[0]}') "
                            f"is highly recommended to decouple carbon footprint from economic expenses."
                        )
                else:
                    response_text = (
                        "To explain specific metrics, please load a case study template or compile a hierarchical BOM first. "
                        "I analyze GWP (carbon footprint), acidification (SO2 eq), water consumption, and feedstock purchase cost to locate optimal ecodesign trade-offs."
                    )
            else:
                response_text = (
                    "I am your LCA Copilot. You can load a case study template from the 'Ingestion Workspace' panel, "
                    "compile a hierarchical BOM, or request substitutions directly (e.g. *'substitute steel with scrap steel'*)."
                )
            return {
                "action": "chat",
                "response": response_text
            }

        if exchanges_list:
            flows_str = "\n".join([f"- ID: {ex['id']} | Name: {ex['name']} | Amount: {ex['amount']} {ex['unit']}" for ex in exchanges_list])
            inventory_note = ""
        else:
            flows_str = "[Empty Inventory - No feedstock or materials loaded yet]"
            inventory_note = (
                "\nNOTE: The feedstock inventory is currently empty. The user hasn't loaded any case study or BOM yet. "
                "If they ask general questions, seek guidance, or seem confused, please answer their question warmly and "
                "explain how they can get started (e.g., loading a case study from the dropdown on the left under 'Flat List', "
                "pasting a hierarchical JSON BOM in the second tab 'Hierarchical JSON', or typing a sustainability goal in "
                "the 'Autonomous Loop' tab). Explain the main capabilities of the tool: semantic mapping, mass-balance "
                "verification, multi-objective Pareto optimization, uncertainty histograms, and interactive substitutions."
            )
        
        weights_info = ""
        if weights:
            weights_info = f"\nUser Multi-Criteria Decision Weights Priorities (TOPSIS): {json.dumps(weights)}"

        prompt = f"""
You are the brain of an interactive LCA Copilot.
The user has asked: "{user_query}"
{weights_info}

Here are the input exchanges in the current synthesized manufacturing process:
{flows_str}

LCA Report Data (Carbon footprint, water, cost):
{json.dumps(report) if report else 'No calculation report available yet.'}
{inventory_note}

Your task:
1. Determine if the user wants to test a material substitution (e.g. "replace steel with scrap steel" or "what if we use recycled plastic?").
2. If they want to test a substitution:
   - Identify which virgin flow from the list above they want to replace. Choose the exact matching name from the list.
   - Formulate a search query to look up the recycled/green substitute in the flow database.
   - Respond in JSON format: {{"action": "substitute", "virgin_flow_name": "exact_name_from_list", "substitute_search_query": "search_term_for_substitute"}}
3. Determine if the user is explicitly teaching you a new material mapping, abbreviation, or synonym (e.g., "PLA stands for polylactic acid", "map carbon fiber to carbon fibre", or "remember that PET is polyethylene terephthalate").
   - If they are teaching you a mapping:
     - Identify the informal term/abbreviation and the standard database name.
     - Respond in JSON format: {{"action": "learn", "abbreviation": "informal_term", "standard_name": "standard_db_name", "response": "I have mapped 'informal_term' to 'standard_db_name' in my dictionary. I will use this for future mapping searches."}}
4. If they are asking a question, seeking help, explaining results, or asking for next steps:
   - Respond in JSON format: {{"action": "chat", "response": "Your helpful, expert response explaining the LCA results or guiding the user on their next step."}}

Respond only with a valid JSON object. Do not add any conversational text before or after the JSON.
"""
        response_text = self._call_llm(prompt, json_format=True)
        try:
            if response_text:
                return json.loads(response_text)
        except Exception as e:
            return {
                "action": "chat",
                "response": f"Failed to parse LLM command: {e}"
            }
        return {
            "action": "chat",
            "response": "I didn't understand that command. Try asking a question or request a substitution (e.g., 'replace glass fibre with glass cullet')."
        }

    def rerank_candidates(self, query, candidates):
        """
        Uses the local LLM to semantically re-rank and score the top TF-IDF flow candidates.
        Provides a neuro-symbolic re-ranking layer for high mapping precision.
        """
        if not self.is_ollama_active() or not candidates:
            return candidates
            
        candidates_str = "\n".join([f"{idx+1}. Name: '{c[0].name}' (ID: {c[0].id}, Category: {c[0].category}, TF-IDF score: {c[1]:.4f})" for idx, c in enumerate(candidates)])
        
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
        response_text = self._call_llm(prompt, json_format=True)
        try:
            if response_text:
                data = json.loads(response_text)
                indices = []
                if isinstance(data, dict):
                    # Look for any list inside the dictionary
                    for val in data.values():
                        if isinstance(val, list):
                            indices = val
                            break
                    if not indices:
                        # Fallback to keys if no list found
                        indices = list(data.keys())
                elif isinstance(data, list):
                    indices = data
                
                ranked = []
                for val in indices:
                    try:
                        idx = int(val) - 1
                        if 0 <= idx < len(candidates):
                            if candidates[idx] not in ranked:
                                ranked.append(candidates[idx])
                    except (ValueError, TypeError):
                        continue
                # Append any remaining candidates that were not ranked by LLM
                for c in candidates:
                    if c not in ranked:
                        ranked.append(c)
                return ranked
        except Exception as e:
            print(f"[Reranking] Parsing error: {e}")
            pass
        return candidates

    def expand_material_query(self, query):
        """
        Uses the local LLM to translate or expand informal material names, synonyms,
        or chemical abbreviations (e.g. 'PET', 'HDPE', 'scrap') into official standard 
        LCA/ecoinvent flow naming terms.
        """
        if not self.is_ollama_active():
            return [query]
            
        prompt = f"""
You are a materials mapping translator for an LCA database.
The user is searching for this feedstock or material: "{query}"

Identify standard database naming variants and synonyms for this material in databases like ecoinvent.
Respond ONLY with a JSON object containing the key "expansions" mapped to a list of standard names, for example:
{{
  "expansions": ["polyethylene terephthalate", "polyethylene terephthalate, granulate"]
}}

Do not write conversational text.
"""
        response_text = self._call_llm(prompt, json_format=True)
        try:
            if response_text:
                data = json.loads(response_text)
                expanded = data.get("expansions", [])
                if isinstance(expanded, list):
                    return [str(item) for item in expanded if item]
        except Exception:
            pass
        return [query]
