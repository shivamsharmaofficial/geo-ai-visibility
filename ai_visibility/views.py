# ai_visibility/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .services.brand_ai_client import enrich_brand_with_llm, BrandAIError
from .services.brand_analysis_service import (
    analyze_brand_visibility,
    BrandVisibilityAIError,
)


# ---------- DASHBOARD & SECTIONS ----------


def dashboard_home(request):
    """
    Main GEO Dashboard overview.
    """
    context = {
        "active_page": "dashboard",
    }
    return render(request, "ai_visibility/dashboard_home.html", context)


def dashboard(request):
    """
    AI Visibility page.
    """
    brand_param = request.GET.get("brand", "").strip()
    brand_name = brand_param or ""

    context = {
        "brand_name": brand_name,
        # These will be updated after analysis with real values (via JS)
        "brand_visibility": 0,
        "avg_rank": 0,
        "citations": "0",
        "competitors": [],
        "error_message": None,
        "active_page": "ai_visibility",
    }

    return render(request, "ai_visibility/dashboard.html", context)

def competitor_view(request):
    """
    Competitor analysis page.
    """
    context = {
        "active_page": "competitor",
    }
    return render(request, "ai_visibility/competitor.html", context)


def sources_view(request):
    """
    Sources page.
    """
    context = {
        "active_page": "sources",
    }
    return render(request, "ai_visibility/sources.html", context)


def prompts_view(request):
    """
    Prompts page.
    """
    context = {
        "active_page": "prompts",
    }
    return render(request, "ai_visibility/prompts.html", context)


def gam_analysis_view(request):
    """
    Gam Analysis page.
    """
    context = {
        "active_page": "gam_analysis",
    }
    return render(request, "ai_visibility/gam_analysis.html", context)


def llm_traffic_view(request):
    """
    LLM Traffic page.
    """
    context = {
        "active_page": "llm_traffic",
    }
    return render(request, "ai_visibility/llm_traffic.html", context)


# ---------- AJAX: BRAND LOOKUP (GEMINI) ----------


@csrf_exempt
def lookup_brand(request):
    """
    Add Brand → Next.

    - Validates brand_name
    - Tries AI enrichment (Gemini via enrich_brand_with_llm)
    - If AI fails, falls back to user input ONLY (no hard error to user)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    brand_name = (payload.get("brand_name") or "").strip()
    brand_desc = (payload.get("brand_description") or "").strip()

    if not brand_name:
        return JsonResponse({"error": "Brand name is required"}, status=400)

    ai_warning = None
    enriched = None

    try:
        enriched = enrich_brand_with_llm(brand_name, brand_desc)
    except BrandAIError as e:
        # Don’t block UX; just log and fall back to user input
        ai_warning = str(e)
        print("WARNING Brand AI failed:", ai_warning)

    if enriched:
        topics_str = "\n".join(enriched.get("initial_topics", []))
        response = {
            "brand_name": enriched.get("brand_name", brand_name),
            "brand_description": enriched.get("brand_description", brand_desc),
            "brand_url": enriched.get("brand_url", ""),
            "region": enriched.get("region", ""),
            "language": enriched.get("language", ""),
            "initial_topics": topics_str,
        }
    else:
        # Fallback: only echo user input, keep the rest empty
        response = {
            "brand_name": brand_name,
            "brand_description": brand_desc,
            "brand_url": "",
            "region": "",
            "language": "",
            "initial_topics": "",
        }

    if ai_warning:
        response["ai_warning"] = ai_warning

    return JsonResponse(response)


# ---------- AJAX: RUN BRAND ANALYSIS (for progress bar + metrics) ----------


@csrf_exempt
def run_brand_analysis(request):
    """
    Called when user clicks 'Create' in the brand modal.

    - Accepts brand config (name, url, region, language, topics)
    - Calls analyze_brand_visibility(), which uses Gemini structured output
      to estimate:
        1. brand mention % vs competitors
        2. avg rank vs competitors
        3. citations
        4. visibility & rank trends
        5. donut: competitor mentions vs brand
        6. top 5 prompts (prompt, model, impact)
      and also returns prompt_stats so the loading bar can show
      'Prompts X / Y' and a percentage.

    The orchestrator returns (for last N days, e.g. 30) a JSON shaped like:

    {
      "brand": {
        "name": "...",
        "url": "...",
        "region": "...",
        "language": "...",
        "initial_topics": "..."
      },
      "time_window": "last_30_days",
      "metrics": {
        "brand_share_pct": float,
        "competitor_shares": [ { "name": str, "share_pct": float }, ... ],
        "avg_rank": float,
        "avg_rank_competitors": [ { "name": str, "avg_rank": float }, ... ],
        "citations": int,
        "trend": {
          "labels": [str, ...],
          "visibility": { brand_or_competitor: [float, ...], ... },
          "avg_rank": { brand_or_competitor: [float, ...], ... }
        },
        "donut": [ { "label": str, "value": float }, ... ],
        "top_prompts": [
          { "prompt": str, "model": str, "impact": "High"|"Medium"|"Low" },
          ...
        ],
        "prompt_stats": { "used": int, "total": int }
      }
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    brand_name = (payload.get("brand_name") or "").strip()
    brand_url = (payload.get("brand_url") or "").strip()
    region = (payload.get("region") or "").strip()
    language = (payload.get("language") or "").strip()
    initial_topics = payload.get("initial_topics") or ""

    if not brand_name:
        return JsonResponse({"error": "Brand name is required"}, status=400)

    try:
        result = analyze_brand_visibility(
            brand_name=brand_name,
            brand_url=brand_url,
            region=region,
            language=language,
            initial_topics=initial_topics,
        )
    except BrandVisibilityAIError as e:
        # Surface a friendly error to frontend; you can also log full details server-side
        return JsonResponse(
            {"error": f"Brand visibility analysis failed: {e}"},
            status=500,
        )
    except Exception as e:
        # Fallback for any unexpected error in the pipeline
        print("ERROR in analyze_brand_visibility:", e)
        return JsonResponse(
            {"error": "Brand analysis failed", "details": str(e)},
            status=500,
        )

    return JsonResponse(result)
