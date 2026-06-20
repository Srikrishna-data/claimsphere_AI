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

import base64
import json
import re
from pathlib import Path

from anthropic import Anthropic

client = Anthropic()


def _encode_image(image_path: Path) -> dict:
    media_type = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def run_agent_3(photo_paths: list[Path], vehicle_make: str, vehicle_model: str) -> dict:
    """
    Returns a dict with the damaged parts found, severity, and an
    estimated total repair cost in dollars.
    """
    content = [
        {
            "type": "text",
            "text": (
                f"This is a damage photo from a {vehicle_make} {vehicle_model} "
                "vehicle insurance claim. Look at the photo(s) and identify:\n"
                "1. Which parts are damaged (e.g. front bumper, headlight, door panel)\n"
                "2. Severity of each: minor, moderate, severe\n"
                "3. A reasonable estimated total repair cost in USD, based on "
                "typical body shop labor and parts pricing for this damage\n\n"
                "Respond with ONLY JSON in this shape:\n"
                '{"damaged_parts": [{"part": "...", "severity": "..."}], '
                '"estimated_cost_usd": number, "notes": "short explanation"}'
            ),
        }
    ]
    for p in photo_paths:
        content.append(_encode_image(p))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": content}],
    )

    cleaned = re.sub(r"^```json\s*|\s*```$", "", response.content[0].text.strip())
    return json.loads(cleaned)
