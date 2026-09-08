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

''''

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
'''


"""
agent_3_cost_estimate.py
------------------------

Agent 3:
1. Analyzes vehicle damage photos using Gemini Vision.
2. Identifies damaged parts and severity.
3. Queries Weaviate for:
   - Relevant repair-cost information
   - Relevant insurance coverage information
4. Uses Gemini to combine the visual findings + retrieved knowledge.
5. Returns a structured repair-cost estimate.

Expected output:

{
    "damaged_parts": [
        {
            "part": "Front Bumper",
            "severity": "moderate"
        }
    ],
    "estimated_cost_usd": 1200,
    "coverage_assessment": "Collision",
    "notes": "The front bumper shows moderate impact damage..."
}
"""

import base64
import json
import os
import re
from pathlib import Path
from typing import List

import weaviate
from weaviate.classes.query import Filter
from groq import Groq
from google import genai

# ============================================================
# API KEYS CONFIGURATION
# Set your Groq API Key below OR set the environment variable GROQ_API_KEY
# ============================================================

#GROQ_API_KEY = "your_groq_api_key_here"  # <--- PLACE YOUR GROQ API KEY HERE

WEAVIATE_URL = "https://ulue7k1nt5ivdmpdydewa.c0.us-east-1.aws.weaviate.cloud"
WEAVIATE_API_KEY = "UG8ybnFTNEVEUi9UVHF3MF9GK0xFYnVrektzNVE5MmRVSDF5dGRCUmdCNmRmQ1FPRXdET3BXMHg2K2lFPV92MjAw"

# Initialize Groq Client

'''
just add the api keys, i am removing as git cannot contain secrets

'''

groq_client = Groq()
gemini_client = genai.Client()


# ============================================================
# IMAGE HELPER FOR GROQ
# ============================================================

def _encode_image_to_base64(path: Path) -> tuple[str, str]:
    """
    Reads an image file, returns its base64 string and MIME type.
    """
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        mime_type = "image/jpeg"
    elif suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"
    else:
        raise ValueError(f"Unsupported image format: {path.suffix}")

    with open(path, "rb") as img_file:
        base64_data = base64.b64encode(img_file.read()).decode("utf-8")

    return base64_data, mime_type


# ============================================================
# JSON PARSER
# ============================================================

def _parse_json(raw: str) -> dict:
    """
    Cleans markdown code fences and parses raw string into JSON dict.
    """
    cleaned = raw.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned.strip())


# ============================================================
# VEHICLE DAMAGE ANALYSIS (GROQ VISION)
# ============================================================

def _analyze_damage(
    photo_paths: List[Path],
    vehicle_make: str,
    vehicle_model: str
) -> dict:
    prompt = f"""
You are an automobile insurance damage assessment assistant.
You are analyzing accident damage photos of a {vehicle_make} {vehicle_model}.

Analyze ALL attached images carefully.

Identify:
1. Every vehicle part that is visibly damaged.
2. The severity of the damage for each damaged part (must be: minor, moderate, or severe).

Rules:
- Only identify damage visibly supported by the images.
- Do NOT assume hidden or internal damage.
- Do NOT estimate repair costs or insurance coverage.
- If a part is not visibly damaged, do not include it.
- If the same part appears in multiple images, list it only once.

Return ONLY valid JSON matching this schema:
{{
    "damaged_parts": [
        {{
            "part": "Front Bumper",
            "severity": "moderate"
        }}
    ]
}}
"""

    # Build Gemini inline_data image parts
    images = []
    for path in photo_paths:
        mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        images.append({
            "inline_data": {
                "mime_type": mime,
                "data": path.read_bytes(),
            }
        })

    # Call Gemini Vision Model
    response = gemini_client.models.generate_content(
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
        config={"temperature": 0.1}
    )

    return _parse_json(response.text)


# ============================================================
# WEAVIATE RETRIEVAL
# ============================================================

def _retrieve_knowledge(
    vehicle_make: str,
    vehicle_model: str,
    damaged_parts: List[dict]
) -> tuple[list, list]:

    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        raise ValueError("Weaviate configuration details missing.")

    repair_cost_docs = []
    coverage_docs = []

    with weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
    ) as client:

        claimsphere_kb = client.collections.get("claimsphere_kb")

        # 1. RETRIEVE REPAIR COST INFORMATION
        repair_response = claimsphere_kb.query.fetch_objects(
            filters=(
                Filter.by_property("knowledge_type").equal("repair_cost")
                & Filter.by_property("make").equal(vehicle_make)
                & Filter.by_property("model").equal(vehicle_model)
            ),
            limit=5
        )

        for obj in repair_response.objects:
            repair_cost_docs.append(obj.properties)

        # 2. RETRIEVE COVERAGE INFORMATION
        damage_description = ", ".join(
            [f"{item.get('part', '')} {item.get('severity', '')} damage" for item in damaged_parts]
        )

        coverage_query = (
            f"Vehicle accident damage involving {damage_description}. "
            f"Determine whether the damage is related to collision, comprehensive coverage, or both."
        )

        coverage_response = claimsphere_kb.query.near_text(
            query=coverage_query,
            filters=Filter.by_property("knowledge_type").equal("coverage"),
            limit=4
        )

        for obj in coverage_response.objects:
            coverage_docs.append(obj.properties)

    return repair_cost_docs, coverage_docs


# ============================================================
# FINAL COST ESTIMATION (GROQ TEXT)
# ============================================================

def _generate_final_estimate(
    vehicle_make: str,
    vehicle_model: str,
    damage_analysis: dict,
    repair_cost_docs: list,
    coverage_docs: list
) -> dict:

    damaged_parts = damage_analysis.get("damaged_parts", [])

    repair_context = json.dumps(repair_cost_docs, indent=2)
    coverage_context = json.dumps(coverage_docs, indent=2)
    damage_context = json.dumps(damaged_parts, indent=2)

    prompt = f"""
You are the final vehicle insurance damage estimation assistant.

Vehicle: {vehicle_make} {vehicle_model}

VISUAL DAMAGE ANALYSIS:
{damage_context}

REPAIR COST KNOWLEDGE RETRIEVED FROM WEAVIATE:
{repair_context}

INSURANCE COVERAGE KNOWLEDGE RETRIEVED FROM WEAVIATE:
{coverage_context}

YOUR TASK:
1. Review damaged parts.
2. Match each part to available repair-cost info from Weaviate.
3. Estimate total repair cost based on severity (minor, moderate, severe).
4. Determine coverage category (Collision, Comprehensive, Full Coverage, Liability Only, Unknown).
5. Explain briefly why coverage applies.

Respond ONLY with valid JSON matching this schema:
{{
    "damaged_parts": [
        {{
            "part": "Front Bumper",
            "severity": "moderate",
            "estimated_repair_cost_usd": 1100
        }}
    ],
    "estimated_cost_usd": 1100,
    "coverage_assessment": "Collision",
    "coverage_reason": "Damage appears consistent with impact from a collision.",
    "notes": "Estimate is based on retrieved repair-cost data."
}}
"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    return _parse_json(response.choices[0].message.content)


# ============================================================
# MAIN AGENT 3 FUNCTION
# ============================================================

def run_agent_3(
    photo_paths: List[Path],
    vehicle_make: str,
    vehicle_model: str
) -> dict:

    print("\n========================================")
    print("AGENT 3 - DAMAGE & COST ESTIMATION")
    print("========================================")
    print(f"Vehicle: {vehicle_make} {vehicle_model}")

    print("\n[1/3] Analyzing damage images via Groq...")
    damage_analysis = _analyze_damage(
        photo_paths=photo_paths,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model
    )
    
    damaged_parts = damage_analysis.get("damaged_parts", [])
    print(f"Detected damaged parts: {len(damaged_parts)}")
    for item in damaged_parts:
        print(f"  - {item.get('part')} ({item.get('severity')})")

    print("\n[2/3] Querying Weaviate knowledge base...")
    repair_cost_docs, coverage_docs = _retrieve_knowledge(
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        damaged_parts=damaged_parts
    )
    print(f"Repair-cost docs retrieved: {len(repair_cost_docs)}")
    print(f"Coverage docs retrieved: {len(coverage_docs)}")

    print("\n[3/3] Generating final estimate via Groq...")
    final_result = _generate_final_estimate(
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        damage_analysis=damage_analysis,
        repair_cost_docs=repair_cost_docs,
        coverage_docs=coverage_docs
    )

    print("\nAgent 3 completed successfully.")
    return final_result