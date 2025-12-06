# ai_visibility/services/amplitude_client.py

from typing import Dict, Any


class AmplitudeError(Exception):
    """
    Custom exception for Amplitude-related errors.

    Right now we are not calling Amplitude APIs, but this class is kept
    for future use when you decide to integrate real Amplitude endpoints.
    """
    pass


def fetch_brand_visibility(brand_name: str) -> Dict[str, Any]:
    """
    Fetch brand visibility metrics for a given brand.

    CURRENT BEHAVIOR (NO CHART ID, NO API, NO DUMMY DATA):
    - Does NOT call Amplitude.
    - Does NOT require API key, secret, region, or chart id.
    - Always returns empty / None values for all metrics.

    This keeps your backend stable while you build the UI and flows.
    Later, you can replace the body of this function with real Amplitude
    logic (events, chart, or custom pipeline) without changing the rest
    of your project.
    """

    # You can log here for debugging if you want:
    # print(f"fetch_brand_visibility called for brand: {brand_name!r}")

    return {
        "brand_visibility": None,  # e.g. percentage later
        "avg_rank": None,          # e.g. average position later
        "citations": None,         # e.g. number of mentions later
        "competitors": [],         # e.g. list of {"name": ..., "visibility": ...}
    }
