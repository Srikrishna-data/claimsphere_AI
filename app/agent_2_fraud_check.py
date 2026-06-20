"""
agent_2_fraud_check.py
------------------------
Agent 2's job, in plain English - this is EXACTLY what you described doing
manually in ChatGPT:
  "I usually give 2 pictures to ChatGPT and check if they are identical."

That is literally a Claude vision API call with two images attached.
You don't need a separate "vision model" or "computer vision tool" -
the same Claude model that read your text in Agent 1 can also look at
images, in the same kind of API call. You just attach images instead
of (or alongside) text.

What this agent does:
  1. Look in our local photo storage for any OLD photos saved under
     this policy number.
  2. If there are old photos, send BOTH the old photo and the new
     photo to Claude in one message, and ask: "are these the same
     photo reused, or genuinely different damage?"
  3. Also ask Claude to sanity-check the photo against the text
     description from Agent 1 (e.g. description says "rear-ended"
     but photo shows front-end damage - that's a red flag).
  4. Return a fraud_score from 0.0 (no concern) to 1.0 (high concern).
"""

import base64
from pathlib import Path

from anthropic import Anthropic

client = Anthropic()

PHOTO_STORAGE_ROOT = Path(__file__).parent.parent / "data" / "photos"


def _encode_image(image_path: Path) -> dict:
    """Reads an image file from disk and base64-encodes it the way the
    Claude API expects for image inputs."""
    media_type = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _get_stored_photos(policy_number: str) -> list[Path]:
    """Looks in data/photos/<policy_number>/ for any previously saved photos."""
    folder = PHOTO_STORAGE_ROOT / policy_number
    if not folder.exists():
        return []
    return sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))


def run_agent_2(policy_number: str, new_photo_paths: list[Path], accident_description: str) -> dict:
    """
    new_photo_paths: the photos the customer just uploaded for THIS claim.
    Returns a dict with fraud_score (0.0-1.0), a plain-English reason,
    and whether this claim should be blocked from going to Agent 3.
    """
    old_photos = _get_stored_photos(policy_number)

    if not old_photos:
        # First-time claim for this policy number - nothing to compare against.
        # We can still do a basic "does the photo match the description" check.
        content = [
            {
                "type": "text",
                "text": (
                    "This is a new vehicle insurance claim. Here is the accident "
                    f"description: \"{accident_description}\"\n\n"
                    "Look at the attached damage photo(s). Does the visible damage "
                    "reasonably match the description? Respond with ONLY JSON: "
                    '{"fraud_score": 0.0-1.0, "reason": "short explanation"}'
                ),
            }
        ]
        for p in new_photo_paths:
            content.append(_encode_image(p))

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": content}],
        )
        result = _parse_json_response(response.content[0].text)
        result["compared_against_history"] = False
        return result

    # We HAVE old photos for this policy - this is the real fraud check:
    # compare the new photo against an old one to catch reused/duplicate images.
    content = [
        {
            "type": "text",
            "text": (
                "You are comparing two vehicle damage photos for fraud detection.\n"
                "IMAGE 1 is from a PAST claim on this policy.\n"
                "IMAGE 2 is from the CURRENT new claim being filed.\n\n"
                f"Current claim's stated accident description: \"{accident_description}\"\n\n"
                "Check for:\n"
                "1. Is IMAGE 2 actually the same photo as IMAGE 1, reused or "
                "lightly edited (a sign of fraud)?\n"
                "2. Does the damage in IMAGE 2 look consistent with the accident "
                "description, or does it look like older/already-repaired damage?\n\n"
                'Respond with ONLY JSON: {"fraud_score": 0.0-1.0, "reason": "short explanation"}'
            ),
        },
        _encode_image(old_photos[0]),
    ]
    for p in new_photo_paths:
        content.append(_encode_image(p))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": content}],
    )
    result = _parse_json_response(response.content[0].text)
    result["compared_against_history"] = True
    return result


def _parse_json_response(raw_text: str) -> dict:
    import json
    import re

    # Claude sometimes wraps JSON in markdown fences despite instructions -
    # this strips that defensively so json.loads doesn't break.
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip())
    parsed = json.loads(cleaned)
    return {
        "fraud_score": float(parsed.get("fraud_score", 0.0)),
        "reason": parsed.get("reason", ""),
    }
