# ai_visibility/services/brand_ai_client.py

import json
from typing import Dict, Any, List
import requests
from django.conf import settings


class BrandAIError(Exception):
    """Raised when the LLM/AI brand enrichment fails."""
    pass


# 💡 1. DEFINE THE REQUIRED JSON SCHEMA
# This schema enforces the exact structure and data types for the enrichment data.
BRAND_ENRICHMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "brand_name": {"type": "string", "description": "The official or recognized brand name."},
        "brand_description": {"type": "string", "description": "A brief, accurate description of the brand and its core business."},
        "brand_url": {"type": "string", "description": "The brand's primary official website URL."},
        "region": {"type": "string", "description": "The primary geographical region the brand targets (e.g., 'India', 'Global', 'North America')."},
        "language": {"type": "string", "description": "The primary language the brand uses (e.g., 'English', 'Hindi')."},
        "initial_topics": {
            "type": "array",
            "description": "3 to 5 high-level keywords or product categories the brand is known for.",
            "items": {"type": "string"}
        },
    },
    "required": [
        "brand_name", 
        "brand_description", 
        "brand_url", 
        "region", 
        "language", 
        "initial_topics"
    ],
}


def enrich_brand_with_llm(brand_name: str, brand_desc_hint: str = "") -> Dict[str, Any]:
    """
    Call Google Gemini API to normalize and enrich brand information using 
    Structured Output with a JSON Schema to guarantee output structure.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise BrandAIError("GEMINI_API_KEY not configured.")

    # ✅ Use v1beta endpoint with structured output support
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # 💡 2. Refined Prompt: Focus on the task, let the schema handle the format
    prompt = (
        "You are a brand intelligence engine. "
        "Your task is to provide accurate, factual information about the given brand. "
        f"Brand Name: {brand_name}\n"
        f"Description Hint (use for context, but fact-check): {brand_desc_hint}\n"
        "Fill in all fields in the required JSON structure. Be realistic and accurate. "
        "If you cannot find a URL, use an empty string."
    )
    
    # 💡 3. Update Request Body with responseSchema
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        # ⬇️ CHANGE 'config' to 'generationConfig' ⬇️
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": BRAND_ENRICHMENT_SCHEMA, 
        }
        # ⬆️ KEY RENAMED ⬆️
    }

    try:
        resp = requests.post(url, json=body, timeout=20)
    except Exception as e:
        raise BrandAIError(f"Network error contacting Gemini API: {e}")

    if resp.status_code != 200:
        try:
            error_data = resp.json()
            # Extract specific error message if available
            error_msg = error_data.get("error", {}).get("message", resp.text[:300])
        except json.JSONDecodeError:
            error_msg = resp.text[:300]
        
        raise BrandAIError(
            f"Gemini API returned {resp.status_code}: {error_msg}"
        )

    data = resp.json()

    try:
        # The response text should now be highly reliable, structured JSON
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # The Gemini service automatically wraps the generated JSON, so we just load the text
        result = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        # This fallback catches unexpected API formats or content blocks
        raise BrandAIError(f"Failed to parse expected JSON structure from Gemini AI: {e}. Raw text start: '{text[:100]}...'")

    # Normalize fields (unchanged, but necessary for clean output)
    brand_name_final = (result.get("brand_name") or brand_name).strip()
    brand_description = (result.get("brand_description") or brand_desc_hint).strip()
    brand_url = (result.get("brand_url") or "").strip()
    region = (result.get("region") or "").strip()
    language = (result.get("language") or "").strip()

    topics_raw = result.get("initial_topics") or []
    if not isinstance(topics_raw, list):
        # Handle case where LLM might return a single string instead of a list (even with schema)
        topics_raw = [topics_raw]
    initial_topics: List[str] = [
        str(t).strip() for t in topics_raw if str(t).strip()
    ]

    return {
        "brand_name": brand_name_final,
        "brand_description": brand_description,
        "brand_url": brand_url,
        "region": region,
        "language": language,
        "initial_topics": initial_topics,
    }