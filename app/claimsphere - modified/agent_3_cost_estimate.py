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

import json
import os
import re
from pathlib import Path
from typing import List

import huggingface_hub
import weaviate
from weaviate.classes.query import Filter
from google import genai
from huggingface_hub import InferenceClient
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# ============================================================
# GEMINI CLIENT
# ============================================================

#client = huggingface_hub.InferenceClient()
import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

MODEL_NAME = "Qwen/Qwen2.5-VL-7B-Instruct"

processor = AutoProcessor.from_pretrained(
    MODEL_NAME
)

model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    torch_dtype="auto",
    device_map="auto"
)
# ============================================================
# WEAVIATE CONFIGURATION
# ============================================================

WEAVIATE_URL = "https://ulue7k1nt5ivdmpdydewa.c0.us-east-1.aws.weaviate.cloud"
WEAVIATE_API_KEY = "UG8ybnFTNEVEUi9UVHF3MF9GK0xFYnVrektzNVE5MmRVSDF5dGRCUmdCNmRmQ1FPRXdET3BXMHg2K2lFPV92MjAw"


# ============================================================
# IMAGE HELPER
# ============================================================

def _image_part(path: Path) -> dict:
    """
    Convert an image into Gemini's inline_data format.
    """

    suffix = path.suffix.lower()

    if suffix in (".jpg", ".jpeg"):
        mime_type = "image/jpeg"

    elif suffix == ".png":
        mime_type = "image/png"

    elif suffix == ".webp":
        mime_type = "image/webp"

    else:
        raise ValueError(
            f"Unsupported image format: {path.suffix}"
        )

    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": path.read_bytes(),
        }
    }


# ============================================================
# JSON PARSER
# ============================================================

def _parse_json(raw: str) -> dict:
    """
    Parse JSON returned by Gemini.

    Handles cases where Gemini accidentally wraps
    the JSON inside ```json ... ```.
    """

    cleaned = raw.strip()

    # Remove markdown code fences
    cleaned = re.sub(
        r"^```json\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"^```\s*",
        "",
        cleaned
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    return json.loads(cleaned.strip())


# ============================================================
# VEHICLE DAMAGE ANALYSIS
# ============================================================
def _analyze_damage(
    photo_paths: List[Path],
    vehicle_make: str,
    vehicle_model: str
) -> dict:

    prompt = f"""
You are an automobile insurance damage assessment assistant.

You are analyzing accident damage photos of a
{vehicle_make} {vehicle_model}.

Analyze ALL attached images carefully.

Identify:

1. Every vehicle part that is visibly damaged.
2. The severity of the damage for each damaged part.

Severity must be EXACTLY one of:

- minor
- moderate
- severe

Rules:

- Only identify damage that is visibly supported by the images.
- Do NOT assume hidden or internal damage.
- Do NOT estimate repair costs.
- Do NOT provide insurance coverage decisions.
- If a part is not visibly damaged, do not include it.
- If the same part appears in multiple images, list it only once.
- Be conservative when determining severity.

Return ONLY valid JSON:

{{
    "damaged_parts": [
        {{
            "part": "Front Bumper",
            "severity": "moderate"
        }}
    ]
}}
"""

    # --------------------------------------------------------
    # Build multimodal message
    # --------------------------------------------------------

    content = [
        {
            "type": "text",
            "text": prompt
        }
    ]

    for path in photo_paths:

        content.append(
            {
                "type": "image",
                "image": str(path)
            }
        )

    messages = [
        {
            "role": "user",
            "content": content
        }
    ]

    # --------------------------------------------------------
    # Prepare inputs
    # --------------------------------------------------------

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )

    inputs = inputs.to(model.device)

    # --------------------------------------------------------
    # Generate response
    # --------------------------------------------------------

    with torch.no_grad():

        generated_ids = model.generate(
            **inputs,
            max_new_tokens=500,
            temperature=0.1
        )

    # Remove the prompt tokens
    generated_ids_trimmed = [
        output_ids[len(input_ids):]
        for input_ids, output_ids
        in zip(inputs["input_ids"], generated_ids)
    ]

    response_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    return _parse_json(response_text)
# ============================================================
# WEAVIATE RETRIEVAL
# ============================================================

def _retrieve_knowledge(
    vehicle_make: str,
    vehicle_model: str,
    damaged_parts: List[dict]
) -> tuple[list, list]:
    """
    Retrieve relevant knowledge from the claimsphere_kb
    Weaviate collection.

    Returns:
        repair_cost_docs
        coverage_docs
    """

    if not WEAVIATE_URL:
        raise ValueError(
            "WEAVIATE_URL environment variable is not set."
        )

    if not WEAVIATE_API_KEY:
        raise ValueError(
            "WEAVIATE_API_KEY environment variable is not set."
        )

    repair_cost_docs = []
    coverage_docs = []

    # --------------------------------------------------------
    # Connect to Weaviate
    # --------------------------------------------------------

    with weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=WEAVIATE_API_KEY
    ) as client:

        claimsphere_kb = client.collections.get(
            "claimsphere_kb"
        )

        # ====================================================
        # 1. RETRIEVE REPAIR COST INFORMATION
        # ====================================================

        # Since the vehicle make/model are already known,
        # use a filtered query rather than relying purely
        # on semantic similarity.

        repair_response = claimsphere_kb.query.fetch_objects(
            filters=(
                Filter.by_property("knowledge_type").equal(
                    "repair_cost"
                )
                & Filter.by_property("make").equal(
                    vehicle_make
                )
                & Filter.by_property("model").equal(
                    vehicle_model
                )
            ),
            limit=5
        )

        for obj in repair_response.objects:

            repair_cost_docs.append(
                obj.properties
            )

        # ====================================================
        # 2. RETRIEVE COVERAGE INFORMATION
        # ====================================================

        # Build a natural-language query using the
        # visually identified damage.

        damage_description = ", ".join(
            [
                f"{item.get('part', '')} "
                f"{item.get('severity', '')} damage"
                for item in damaged_parts
            ]
        )

        coverage_query = (
            f"Vehicle accident damage involving "
            f"{damage_description}. "
            f"Determine whether the damage is related to "
            f"collision, comprehensive coverage, or both."
        )

        coverage_response = claimsphere_kb.query.near_text(
            query=coverage_query,
            filters=Filter.by_property(
                "knowledge_type"
            ).equal("coverage"),
            limit=4
        )

        for obj in coverage_response.objects:

            coverage_docs.append(
                obj.properties
            )

    return repair_cost_docs, coverage_docs


# ============================================================
# FINAL COST ESTIMATION
# ============================================================

def _generate_final_estimate(
    vehicle_make: str,
    vehicle_model: str,
    damage_analysis: dict,
    repair_cost_docs: list,
    coverage_docs: list
) -> dict:
    """
    Ask Gemini to combine:

    - Visual damage analysis
    - Weaviate repair-cost information
    - Weaviate coverage information

    and produce the final estimate.
    """

    damaged_parts = damage_analysis.get(
        "damaged_parts",
        []
    )

    # --------------------------------------------------------
    # Convert retrieved repair documents into readable text
    # --------------------------------------------------------

    repair_context = json.dumps(
        repair_cost_docs,
        indent=2
    )

    coverage_context = json.dumps(
        coverage_docs,
        indent=2
    )

    damage_context = json.dumps(
        damaged_parts,
        indent=2
    )

    prompt = f"""
You are the final vehicle insurance damage estimation assistant.

Vehicle:
Make: {vehicle_make}
Model: {vehicle_model}

==================================================
VISUAL DAMAGE ANALYSIS
==================================================

{damage_context}

==================================================
REPAIR COST KNOWLEDGE RETRIEVED FROM WEAVIATE
==================================================

{repair_context}

==================================================
INSURANCE COVERAGE KNOWLEDGE RETRIEVED FROM WEAVIATE
==================================================

{coverage_context}

==================================================
YOUR TASK
==================================================

Using ONLY the information above:

1. Review the damaged parts identified from the images.

2. Match each damaged part to the closest available
   repair-cost information from the Weaviate knowledge base.

3. Use the severity identified from the images:
   - minor
   - moderate
   - severe

4. Estimate the total repair cost.

5. Determine the most appropriate coverage category:
   - Collision
   - Comprehensive
   - Full Coverage (Collision + Comprehensive)
   - Liability Only
   - Unknown

6. Explain briefly why that coverage category is relevant.

IMPORTANT:
- Do not invent repair prices that are not supported
  by the retrieved repair-cost knowledge.
- If the exact vehicle/model does not exist in the
  knowledge base, clearly say that the repair estimate
  is based on the closest available information.
- The repair-cost values are ranges. Use a reasonable
  value within the range.
- Do not treat the estimate as an official insurance quote.
- If the available knowledge is insufficient, say so.

Respond with ONLY valid JSON:

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
    "notes": "Estimate is based on the retrieved vehicle repair-cost data."
}}
"""

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    return _parse_json(response.text)


# ============================================================
# MAIN AGENT 3 FUNCTION
# ============================================================

def run_agent_3(
    photo_paths: List[Path],
    vehicle_make: str,
    vehicle_model: str
) -> dict:
    """
    Main entry point used by main_app.py.

    Parameters:
        photo_paths:
            List of vehicle damage image paths.

        vehicle_make:
            Example: "Toyota"

        vehicle_model:
            Example: "Camry"

    Returns:
        {
            "damaged_parts": [...],
            "estimated_cost_usd": 1200,
            "coverage_assessment": "Collision",
            "coverage_reason": "...",
            "notes": "..."
        }
    """

    print("\n========================================")
    print("AGENT 3 - DAMAGE & COST ESTIMATION")
    print("========================================")

    print(
        f"Vehicle: {vehicle_make} {vehicle_model}"
    )

    # --------------------------------------------------------
    # STEP 1: Analyze images
    # --------------------------------------------------------

    print("\n[1/3] Analyzing damage images...")

    damage_analysis = _analyze_damage(
        photo_paths=photo_paths,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model
    )

    print("Damage analysis completed.")

    damaged_parts = damage_analysis.get(
        "damaged_parts",
        []
    )

    print(
        f"Detected damaged parts: {len(damaged_parts)}"
    )

    for item in damaged_parts:

        print(
            f"  - {item.get('part')} "
            f"({item.get('severity')})"
        )

    # --------------------------------------------------------
    # STEP 2: Query Weaviate
    # --------------------------------------------------------

    print("\n[2/3] Querying Weaviate knowledge base...")

    repair_cost_docs, coverage_docs = _retrieve_knowledge(
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        damaged_parts=damaged_parts
    )

    print(
        f"Repair-cost documents retrieved: "
        f"{len(repair_cost_docs)}"
    )

    print(
        f"Coverage documents retrieved: "
        f"{len(coverage_docs)}"
    )

    # --------------------------------------------------------
    # STEP 3: Generate final estimate
    # --------------------------------------------------------

    print("\n[3/3] Generating final estimate...")

    final_result = _generate_final_estimate(
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        damage_analysis=damage_analysis,
        repair_cost_docs=repair_cost_docs,
        coverage_docs=coverage_docs
    )

    print("\nAgent 3 completed.")

    return final_result