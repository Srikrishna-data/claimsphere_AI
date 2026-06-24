"""
agent_3_cost_estimate.py
--------------------------
Agent 3's job, in plain English:
  "Scan the images again and tell what is the estimated cost for repair."

This is the SAME pattern as Agent 2 - attach images to a Claude API call.
The only difference is what we're asking Claude to look for: instead of
"is this fraud", we're asking "what's damaged and roughly what does
fixing that cost."

This agent ONLY runs if Agent 2 did not flag fraud - that gating logic
lives in main_app.py as a plain "if" statement, no special tool needed.

The cost numbers Claude returns are estimates from general knowledge of
repair costs - good enough for a demo/learning project. For a real
production system you'd eventually want to ground this in an actual
parts-and-labor price list rather than relying purely on the model's
judgment.
"""
"""
Agent 3 (Gemini Vision — FINAL FIXED VERSION)
Damage + cost estimation.
"""

import json
import re
from pathlib import Path
from typing import List

from google import genai

client = genai.Client()


def _image_part(path: Path) -> dict:
    """Return correct Gemini inline_data format."""
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {
        "inline_data": {
            "mime_type": mime,
            "data": path.read_bytes(),
        }
    }


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
    return json.loads(cleaned)


def run_agent_3(photo_paths: List[Path], vehicle_make: str, vehicle_model: str) -> dict:
    """
    Returns:
      {
        "damaged_parts": [{"part": "...", "severity": "..."}],
        "estimated_cost_usd": number,
        "notes": "short explanation"
      }
    """
    prompt = (
        f"You are analyzing damage photos from a {vehicle_make} {vehicle_model}.\n"
        "Look at the attached photo(s) and identify:\n"
        "1. Damaged parts (e.g., bumper, headlight, fender)\n"
        "2. Severity: minor, moderate, severe\n"
        "3. Estimated total repair cost in USD (reasonable body shop estimate)\n\n"
        "Respond with ONLY JSON:\n"
        '{"damaged_parts":[{"part":"...","severity":"..."}],'
        '"estimated_cost_usd":1234,'
        '"notes":"short explanation"}'
    )

    images = [_image_part(p) for p in photo_paths]

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    *images
                ]
            }
        ],
    )

    return _parse_json(response.text)
