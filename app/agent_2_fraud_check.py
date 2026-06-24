"""
Agent 2 (Gemini Vision — FINAL FIXED VERSION)
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


def run_agent_2(policy_number: str, new_photo_paths: List[Path], accident_description: str) -> dict:
    # Load old photos
    old_folder = Path(__file__).parent.parent / "data" / "photos" / policy_number
    old_photos = sorted(old_folder.glob("*.jpg")) + sorted(old_folder.glob("*.png"))

    # Convert new photos
    new_images = [_image_part(p) for p in new_photo_paths]

    # -------------------------------
    # CASE 1: No old photos
    # -------------------------------
    if not old_photos:
        prompt = (
            "This is a new vehicle insurance claim.\n"
            f"Accident description: \"{accident_description}\"\n\n"
            "Look at the attached damage photo(s). Does the visible damage "
            "reasonably match the description?\n\n"
            "Respond with ONLY JSON:\n"
            '{"fraud_score": 0.0-1.0, "reason": "short explanation"}'
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        *new_images
                    ]
                }
            ],
        )

        result = _parse_json(response.text)
        result["compared_against_history"] = False
        return result

    # -------------------------------
    # CASE 2: Old photos exist → compare
    # -------------------------------
    old_image = _image_part(old_photos[0])

    prompt = (
        "You are comparing two sets of vehicle damage photos for fraud detection.\n"
        "IMAGE SET 1 = past claim\n"
        "IMAGE SET 2 = current claim\n\n"
        f"Accident description: \"{accident_description}\"\n\n"
        "Check:\n"
        "1. Are the new photos reused or lightly edited versions of the old ones?\n"
        "2. Does the new damage match the description?\n\n"
        "Respond with ONLY JSON:\n"
        '{"fraud_score": 0.0-1.0, "reason": "short explanation"}'
    )

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    old_image,
                    *new_images
                ]
            }
        ],
    )

    result = _parse_json(response.text)
    result["compared_against_history"] = True
    return result
