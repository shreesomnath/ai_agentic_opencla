import requests
import json

class LcaLlmAgent:
    """
    Interfaces with a local Ollama server running open-source LLMs 
    (such as qwen2.5-coder:7b) to provide natural language reasoning,
    hotspot interpretation, and engineering reports.
    """
    def __init__(self, ollama_url="http://localhost:11434", model="qwen2.5-coder:7b"):
        self.ollama_url = ollama_url
        self.model = model

    def is_ollama_active(self):
        """
        Checks if the local Ollama server is active and accessible.
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def generate_engineering_justification(self, report):
        """
        Interprets a Multi-Objective LCA trade-off report and generates 
        a formal engineering justification text (e.g. for NSF proposals or ESG reports).
        """
        if not self.is_ollama_active():
            return (
                "LLM justification could not be generated: Local Ollama server is offline. "
                "Please run 'ollama run qwen2.5-coder:7b' in your terminal."
            )

        # Formulate prompt from report metrics
        metrics = report.get("metrics", {})
        gwp = metrics.get("Global Warming", {})
        acid = metrics.get("Acidification", {})
        water = metrics.get("Water Consumption", {})
        cost = metrics.get("Feedstock Cost", {})

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

Instructions:
- Interpret whether this substitution is "Pareto-improving" (decoupling environmental footprints without raising costs).
- Explain the physical and chemical reason why replacing virgin components (like glass fibers) with secondary raw materials (like sorted glass cullet) yields these benefits.
- Summarize the multi-dimensional savings (carbon, acidification, water, cost).
- Keep the tone academic, precise, and professional. Output only the finished justification paragraph (no conversational prefixes like 'Here is your paragraph').
"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=60)
            if response.status_code == 200:
                result_json = response.json()
                return result_json.get("response", "").strip()
            else:
                return f"Ollama API Error: HTTP {response.status_code} - {response.text}"
        except Exception as e:
            return f"Failed to generate LLM text: {e}"

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

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=15)
            if response.status_code == 200:
                result_json = response.json()
                content = result_json.get("response", "").strip()
                return json.loads(content)
            else:
                return [f"{hotspot_flow_name.split(',')[0]} recycled"]
        except Exception:
            return [f"{hotspot_flow_name.split(',')[0]} recycled"]
