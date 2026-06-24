import requests
import json

url = "http://localhost:11434/api/generate"
model = "qwen2.5-coder:7b"

prompt = """
You are a materials mapping translator for an LCA database.
User query: "PET"

Translate this search term into standard database naming variants.
If it is an abbreviation (like PET, HDPE, PVC, scrap), expand it to its standard chemical/material names (e.g. "polyethylene terephthalate", "polyethylene, high density", "scrap steel").
Provide up to 3 standard names or synonyms in a JSON array of strings.
Example for "PET": ["polyethylene terephthalate", "polyethylene terephthalate, granulate"]
Example for "tap water": ["tap water", "water, tap"]

Respond ONLY with a valid JSON array of strings. Do not write conversational text.
"""

payload = {
    "model": model,
    "prompt": prompt,
    "stream": False,
    "format": "json"
}

try:
    res = requests.post(url, json=payload, timeout=10)
    print("HTTP Status:", res.status_code)
    print("Response JSON:")
    print(res.json())
    print("Raw Response text field:")
    print(res.json().get("response"))
except Exception as e:
    print("Error:", e)
