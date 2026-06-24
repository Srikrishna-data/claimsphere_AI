"""
Agent 1 (Groq version — updated model)
Extracts structured fields from the claim form using LLaMA‑3.1 70B on Groq.

changed to model="llama-3.3-70b-versatile"
"""
"""
Agent 1 (Groq version — with JSON extraction)
"""

import json
import re
from groq import Groq

from database import get_claim_history

client = Groq()

EXTRACTION_PROMPT = """You are reading a vehicle insurance claim form.
Extract the following fields and return ONLY a JSON object, nothing else:

{
  "customer_name": string,
  "policy_number": string,
  "vehicle_make": string,
  "vehicle_model": string,
  "accident_date": "YYYY-MM-DD",
  "accident_description": string
}

If a field is missing, use an empty string.

Here is the claim form text:
"""


def _extract_json(text: str) -> dict:
    """
    Extracts the first JSON object found in the model output.
    Works even if the model adds extra text.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output:\n" + text)
    return json.loads(match.group(0))


def run_agent_1(claim_form_text: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT + claim_form_text}
        ],
        temperature=0.2,
        max_tokens=512,
    )

    raw_text = response.choices[0].message.content.strip()

    # Extract JSON safely
    extracted_fields = _extract_json(raw_text)

    # Lookup history
    policy_number = extracted_fields.get("policy_number", "")
    history = get_claim_history(policy_number) if policy_number else []

    past_claim_count = len(history)
    total_past_payout = sum(c["claim_amount"] for c in history)
    has_fraud_flag_history = any(c["status"] == "flagged_fraud" for c in history)

    return {
        "extracted_fields": extracted_fields,
        "claim_history": {
            "past_claim_count": past_claim_count,
            "total_past_payout": total_past_payout,
            "has_fraud_flag_history": has_fraud_flag_history,
            "claims": history,
        },
    }
