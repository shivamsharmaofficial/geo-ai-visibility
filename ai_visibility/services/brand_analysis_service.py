# ai_visibility/services/brand_analysis_service.py

import json
from typing import Dict, Any
import requests
from django.conf import settings


class BrandVisibilityAIError(Exception):
    """
    Raised when Gemini brand visibility analysis fails.
    """
    pass


# -------------------------------------------------------------------
# JSON schema for Gemini structured output – must match frontend needs
# -------------------------------------------------------------------

BRAND_VISIBILITY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "brand_share_pct": {
            "type": "number",
            "description": (
                "Estimated percentage of AI responses (across major models) "
                "that mention the brand compared to its competitors for the "
                "given topics and region."
            ),
        },
        "competitor_shares": {
            "type": "array",
            "description": "Estimated share-of-voice percentage for each competitor brand.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "share_pct": {"type": "number"},
                },
                "required": ["name", "share_pct"],
            },
        },
        "avg_rank": {
            "type": "number",
            "description": (
                "Estimated average rank/position of the brand when it appears in "
                "AI responses for relevant prompts (lower is better)."
            ),
        },
        "avg_rank_competitors": {
            "type": "array",
            "description": "Estimated average rank for the brand and key competitors.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "avg_rank": {"type": "number"},
                },
                "required": ["name", "avg_rank"],
            },
        },
        "citations": {
            "type": "integer",
            "description": (
                "Estimated count of AI responses that explicitly reference the "
                "brand's official website or URL for the chosen topics and "
                "time window."
            ),
        },
        "trend": {
            "type": "object",
            "description": "Time-series trends for visibility and average rank.",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Time labels (e.g., dates) for each point in the trend.",
                },
                # Visibility series: list of { name, values[] }
                "visibility": {
                    "type": "array",
                    "description": (
                        "List of brands with visibility share-of-voice time series. "
                        "Each item has a brand name and an array of numeric values "
                        "aligned with 'labels'."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "values": {
                                "type": "array",
                                "items": {"type": "number"},
                            },
                        },
                        "required": ["name", "values"],
                    },
                },
                # Avg rank series: list of { name, values[] }
                "avg_rank": {
                    "type": "array",
                    "description": (
                        "List of brands with average-rank time series. "
                        "Each item has a brand name and an array of numeric "
                        "values aligned with 'labels'."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "values": {
                                "type": "array",
                                "items": {"type": "number"},
                            },
                        },
                        "required": ["name", "values"],
                    },
                },
            },
            "required": ["labels", "visibility", "avg_rank"],
        },
        "donut": {
            "type": "array",
            "description": "Data for the competitor-vs-brand donut chart.",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "number"},
                },
                "required": ["label", "value"],
            },
        },
        "top_prompts": {
            "type": "array",
            "description": "Top 5 prompts that most strongly drive visibility for the brand.",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string"},
                    "impact": {
                        "type": "string",
                        "description": "Impact level: High, Medium, or Low.",
                    },
                },
                "required": ["prompt", "model", "impact"],
            },
        },
        "prompt_stats": {
            "type": "object",
            "description": "Internal estimate of how many prompts were considered.",
            "properties": {
                "used": {"type": "integer"},
                "total": {"type": "integer"},
            },
            "required": ["used", "total"],
        },
    },
    "required": [
        "brand_share_pct",
        "competitor_shares",
        "avg_rank",
        "avg_rank_competitors",
        "citations",
        "trend",
        "donut",
        "top_prompts",
        "prompt_stats",
    ],
}


# -------------------------------------------------------------------
# Low-level Gemini call
# -------------------------------------------------------------------

def _call_gemini_for_visibility(prompt: str) -> Dict[str, Any]:
    """
    Low-level helper: call Gemini with the given prompt and BRAND_VISIBILITY_SCHEMA.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise BrandVisibilityAIError("GEMINI_API_KEY not configured for visibility analysis.")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": BRAND_VISIBILITY_SCHEMA,
        },
    }

    try:
        resp = requests.post(url, json=body, timeout=40)
    except Exception as e:
        raise BrandVisibilityAIError(f"Network error contacting Gemini for visibility: {e}")

    if resp.status_code != 200:
        try:
            error_data = resp.json()
            error_msg = error_data.get("error", {}).get("message", resp.text[:300])
        except json.JSONDecodeError:
            error_msg = resp.text[:300]

        raise BrandVisibilityAIError(
            f"Gemini visibility API returned {resp.status_code}: {error_msg}"
        )

    data = resp.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise BrandVisibilityAIError(
            f"Failed to parse visibility JSON structure from Gemini: {e}."
        )

    return result


# -------------------------------------------------------------------
# High-level orchestration – called from Django view
# -------------------------------------------------------------------

def analyze_brand_visibility(
    brand_name: str,
    brand_url: str,
    region: str,
    language: str,
    initial_topics: str,
) -> Dict[str, Any]:
    """
    High-level orchestrator used by the Django view.

    Uses Gemini as a 'brand visibility and search analytics analyst':
    - Estimates share-of-voice vs competitors
    - Estimates average rank vs competitors
    - Estimates citations (website mentions)
    - Builds visibility & rank trends
    - Builds donut chart data
    - Suggests top prompts
    - Returns prompt_stats for the loading bar

    NOTE: These are *AI estimations* based on Gemini's knowledge and public web context,
    not exact logs from real AI products.
    """

    topics_hint = initial_topics.strip() if isinstance(initial_topics, str) else ""
    region_hint = region or "Global"
    language_hint = language or "English"

    prompt = (
        "You are an AI brand visibility and search analytics expert.\n"
        "You have access to the public web and your own knowledge, but you do NOT have access "
        "to proprietary usage logs from ChatGPT, Gemini, Claude, Llama or other assistants.\n\n"

        "Your job is to build a realistic, internally-consistent ANALYTICS SNAPSHOT for the given brand, "
        "as if you had a dashboard of AI-search usage. You must strictly output JSON that matches the "
        "provided JSON schema. Do NOT add any extra top-level fields, do NOT add comments, and do NOT "
        "return markdown.\n\n"

        "First, use the brand name, region, language and topics to understand:\n"
        "  • What the brand sells and how strong / popular it is in its market.\n"
        "  • The brand's main official website.\n"
        "  • Around 10 meaningful competitors in the same category and region.\n"
        "Then, using your best judgement and web knowledge, construct a plausible analytics dataset that "
        "fills ALL required fields of the JSON schema:\n\n"

        "1) brand_share_pct (number)\n"
        "   - Your estimate of the brand's overall 'share of voice' in AI assistant answers for the last ~30 days.\n"
        "   - This is the % of relevant AI responses that mention the brand, compared to its competitors, "
        "     across the given topics and region.\n"
        "   - Must be between 0 and 100.\n\n"

        "2) competitor_shares (array)\n"
        "   - A list of competitors and their share_pct values.\n"
        "   - Include around 8–10 key competitors where possible.\n"
        "   - brand_share_pct + sum(all competitor share_pct) should be close to 100 (allow small rounding error).\n"
        "   - Use realistic competitor brand names for this category and region.\n\n"

        "3) avg_rank and avg_rank_competitors\n"
        "   - avg_rank: estimated average position where the brand appears in AI answer lists when it is present.\n"
        "     Lower numbers are better (e.g. 1–10 range is typical).\n"
        "   - avg_rank_competitors: include the brand itself plus several main competitors with their avg_rank.\n"
        "   - The stronger brands should generally have lower (better) avg_rank numbers.\n\n"

        "4) citations\n"
        "   - An INTEGER estimate of how many AI responses in the last ~30 days explicitly reference or link to the "
        "     brand's official website (citations).\n"
        "   - Scale this number to the brand's size. Big global brands can be in the thousands; small brands can be "
        "     in the tens or hundreds.\n\n"

        "5) trend (labels, visibility, avg_rank)\n"
        "   - Build a time-series over the last ~30 days with 5–8 points.\n"
        "   - 'labels' should be user-friendly time labels, for example: 'Day 1', 'Day 5', 'Day 10', ... OR short dates.\n"
        "   - 'visibility' must be an ARRAY of objects. Each object:\n"
        "       { \"name\": \"<brand or competitor>\", \"values\": [v1, v2, ...] }\n"
        "     where 'values' is a numeric array of share-of-voice % aligned with 'labels'.\n"
        "   - 'avg_rank' must be an ARRAY of objects with the SAME structure, but 'values' are average rank numbers.\n"
        "   - ALWAYS include the main brand name as one of the 'name' entries in BOTH arrays.\n"
        "   - Also include 2–4 important competitors.\n"
        "   - All 'values' arrays MUST have the same length as 'labels'.\n"
        "   - The curves should look realistic: small fluctuations, no impossible jumps.\n\n"

        "6) donut\n"
        "   - An array for the brand vs competitors donut chart.\n"
        "   - At minimum, include TWO entries:\n"
        "       { \"label\": \"<brand_name>\", \"value\": brand_share_pct }\n"
        "       { \"label\": \"Competitors\", \"value\": 100 - brand_share_pct }\n"
        "   - You may optionally break competitors into multiple slices, but they must be consistent with "
        "     brand_share_pct and competitor_shares.\n\n"

        "7) top_prompts\n"
        "   - A list of the top 5 prompts that people would realistically type into AI assistants when searching for "
        "     this brand or its category.\n"
        "   - Each item must have:\n"
        "       • prompt: a natural language user query (e.g. 'best budget wireless earbuds like <brand_name>')\n"
        "       • model: a realistic LLM model name such as 'gpt-4o', 'gpt-4o-mini', "
        "                 'gemini-2.5-flash', 'claude-3-5-sonnet', 'llama-3-70b', etc.\n"
        "       • impact: one of 'High', 'Medium', 'Low', representing how strongly this prompt contributes to the "
        "                 brand's visibility in AI answers.\n"
        "   - Provide at least two prompts with impact = 'High', at least two with 'Medium'.\n"
        "   - Sort the list from highest to lowest impact.\n\n"

        "8) prompt_stats\n"
        "   - used: integer estimate of how many prompts you effectively considered or simulated for this analysis.\n"
        "   - total: integer estimate of the broader prompt space.\n"
        "   - Ensure used <= total.\n"
        "   - Typical ranges might be between 10 and 200.\n\n"

        "IMPORTANT CONSTRAINTS:\n"
        "  • You MUST fully satisfy the given JSON schema. Fill every required field.\n"
        "  • Do NOT add extra top-level fields beyond those in the schema.\n"
        "  • Do NOT output explanations, comments, or markdown – ONLY a single JSON object.\n"
        "  • Ensure all numeric values are valid JSON numbers (no NaN, no Infinity).\n"
        "  • Ensure arrays and objects are internally consistent (lengths match, names match between sections).\n\n"
        f"Brand name: {brand_name}\n"
        f"User-supplied brand URL (may be empty or approximate): {brand_url or 'unknown'}\n"
        f"Target region: {region_hint}\n"
        f"Primary language: {language_hint}\n"
        f"User-provided initial topics / categories (one per line, optional):\n"
        f"{topics_hint or '[not specified]'}\n\n"
        "Now generate the JSON object matching the schema."
    )

    metrics = _call_gemini_for_visibility(prompt)

    # Wrap metrics with basic brand context – matches what your frontend expects
    result: Dict[str, Any] = {
        "brand": {
            "name": brand_name,
            "url": brand_url,
            "region": region_hint,
            "language": language_hint,
            "initial_topics": topics_hint,
        },
        "time_window": "last_30_days",
        "metrics": metrics,
    }
    return result
