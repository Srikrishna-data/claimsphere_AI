"""
agent_1_intake.py
------------------
Agent 1's job, in plain English:
  1. Read the claim form (the text the customer typed or uploaded).
  2. Ask Claude to pull out the important fields: name, policy number,
     vehicle info, accident date, what happened.
  3. Look that policy number up in our database to see their claim history.
  4. Hand both pieces of info to Agent 2.

There is no "framework" here. This is one function that:
  - makes one API call to Claude
  - makes one database query
  - returns a Python dictionary

That dictionary IS the hand-off to the next agent. You don't need
LangGraph's "state" concept - a dict you pass into the next function
call already does the same job.
"""

import json

from anthropic import Anthropic

from utils.database import get_claim_history

client = Anthropic()  # reads ANTHROPIC_API_KEY from your environment automatically

EXTRACTION_PROMPT = """You are reading a vehicle insurance claim form.
Extract the following fields and return ONLY a JSON object, nothing else,
no markdown code fences, no explanation:

{
  "customer_name": string,
  "policy_number": string,
  "vehicle_make": string,
  "vehicle_model": string,
  "accident_date": "YYYY-MM-DD",
  "accident_description": string
}

If a field is missing from the text, use an empty string for it.

Here is the claim form text:
"""


def run_agent_1(claim_form_text: str) -> dict:
    """
    Takes the raw text from the uploaded claim form.
    Returns a dict with the extracted fields AND the customer's claim history.
    """
    # --- Step 1: ask Claude to extract structured fields from free text ---
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT + claim_form_text}
        ],
    )

    raw_text = response.content[0].text.strip()
    extracted_fields = json.loads(raw_text)

    # --- Step 2: look up this policy number's claim history in our database ---
    policy_number = extracted_fields.get("policy_number", "")
    history = get_claim_history(policy_number) if policy_number else []

    past_claim_count = len(history)
    total_past_payout = sum(c["claim_amount"] for c in history)
    has_fraud_flag_history = any(c["status"] == "flagged_fraud" for c in history)

    # --- Step 3: package everything into one dict for Agent 2 ---
    return {
        "extracted_fields": extracted_fields,
        "claim_history": {
            "past_claim_count": past_claim_count,
            "total_past_payout": total_past_payout,
            "has_fraud_flag_history": has_fraud_flag_history,
            "claims": history,
        },
    }
