"""
agent_4_report.py
--------------------
Agent 4's job, in plain English:
  "Combine the info of all 3 agents and give a PDF."

No AI call needed here at all - this agent just takes the Python dicts
that Agents 1, 2, and 3 already produced, and formats them into a PDF
using the `fpdf2` library. This is the simplest agent in the whole
pipeline, which is exactly what a "combine and format" step should be.
"""

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"


def run_agent_4(
    intake_result: dict,
    fraud_result: dict,
    cost_result: dict | None,
    final_status: str,
) -> Path:
    """
    Builds a one-page PDF summarizing the full claim decision and
    returns the file path it was saved to.

    cost_result is None when the claim was flagged as fraud and
    Agent 3 never ran.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    fields = intake_result["extracted_fields"]
    history = intake_result["claim_history"]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "ClaimSphere AI - Claim Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    _section(pdf, "Claimant information")
    _row(pdf, "Name", fields.get("customer_name", ""))
    _row(pdf, "Policy number", fields.get("policy_number", ""))
    _row(pdf, "Vehicle", f"{fields.get('vehicle_make', '')} {fields.get('vehicle_model', '')}")
    _row(pdf, "Accident date", fields.get("accident_date", ""))
    _row(pdf, "Description", fields.get("accident_description", ""))

    _section(pdf, "Claim history")
    _row(pdf, "Past claims on file", str(history["past_claim_count"]))
    _row(pdf, "Total past payout", f"${history['total_past_payout']:,.2f}")
    _row(pdf, "Prior fraud flags", "Yes" if history["has_fraud_flag_history"] else "No")

    _section(pdf, "Fraud check (Agent 2)")
    _row(pdf, "Fraud score", f"{fraud_result['fraud_score']:.2f} (0 = none, 1 = high concern)")
    _row(pdf, "Reasoning", fraud_result["reason"])

    if cost_result:
        _section(pdf, "Repair cost estimate (Agent 3)")
        _row(pdf, "Estimated cost", f"${cost_result['estimated_cost_usd']:,.2f}")
        for part in cost_result.get("damaged_parts", []):
            _row(pdf, f"  - {part['part']}", part["severity"])
        _row(pdf, "Notes", cost_result.get("notes", ""))
    else:
        _section(pdf, "Repair cost estimate")
        _row(pdf, "Status", "Not calculated - claim was flagged for fraud review")

    _section(pdf, "Final decision")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, final_status.upper(), new_x="LMARGIN", new_y="NEXT")

    policy_number = fields.get("policy_number", "unknown")
    output_path = REPORTS_DIR / f"claim_report_{policy_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(str(output_path))
    return output_path


def _section(pdf: FPDF, title: str):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "", 10)


def _row(pdf: FPDF, label: str, value: str):
    label_width = 45
    start_x = pdf.l_margin
    start_y = pdf.get_y()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(start_x, start_y)
    pdf.cell(label_width, 7, f"{label}:")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(start_x + label_width, start_y)
    value_width = pdf.w - pdf.r_margin - (start_x + label_width)
    pdf.multi_cell(value_width, 7, str(value) if str(value).strip() else "-")
