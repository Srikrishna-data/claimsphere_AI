import sys
from pathlib import Path

import streamlit as st

# allow "from utils.database import ..." to work when run via `streamlit run app/main_app.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent_1_intake import run_agent_1
from app.agent_2_fraud_check import run_agent_2
from app.agent_3_cost_estimate import run_agent_3
from app.agent_4_report import run_agent_4
from utils.database import init_db, insert_claim, seed_sample_data

FRAUD_THRESHOLD = 0.6  # above this score, we stop and flag for human review

PHOTO_STORAGE_ROOT = Path(__file__).parent.parent / "data" / "photos"

st.title("Claimsphere AI ")
st.header("Agentic Insurance Claims System!")


#st.set_page_config(page_title="ClaimSphere AI", page_icon="🚗")

def login_screen():
    st.write("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        # hardcoded demo credentials - replace with real auth before sharing publicly
        if username == "adjuster" and password == "demo123":
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid credentials. Try username: adjuster / password: demo123")


def save_uploaded_photos(policy_number: str, uploaded_files) -> list[Path]:
    """Saves uploaded Streamlit file objects to data/photos/<policy_number>/ on disk."""
    folder = PHOTO_STORAGE_ROOT / policy_number
    folder.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for i, file in enumerate(uploaded_files):
        suffix = Path(file.name).suffix or ".jpg"
        out_path = folder / f"claim_{i}{suffix}"
        out_path.write_bytes(file.getvalue())
        saved_paths.append(out_path)
    return saved_paths


def claim_processing_screen():
    st.title("ClaimSphere AI - Submit a claim")
    st.caption("Logged in as adjuster")

    claim_form_text = st.text_area(
        "Claim form details",
        placeholder=(
            "Example:\nName: Jane Doe\nPolicy Number: POL-1001\n"
            "Vehicle: 2020 Toyota Camry\nAccident Date: 2026-06-10\n"
            "Description: Rear-ended at a stop light, bumper and trunk damaged."
        ),
        height=160,
    )

    uploaded_photos = st.file_uploader(
        "Upload accident photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if st.button("Process claim", type="primary"):
        if not claim_form_text.strip():
            st.error("Please enter claim form details first.")
            return
        if not uploaded_photos:
            st.error("Please upload at least one accident photo.")
            return

        # -------------------------------------------------------------
        # AGENT 1: read form, check claim history
        # -------------------------------------------------------------
        with st.spinner("Agent 1: reading form and checking claim history..."):
            intake_result = run_agent_1(claim_form_text)

        fields = intake_result["extracted_fields"]
        policy_number = fields.get("policy_number", "UNKNOWN")

        st.subheader("Agent 1 - Intake result")
        st.json(intake_result)

        # Save the uploaded photos to disk now, under this policy number,
        # so Agent 2 can find "old" photos for this same policy on future claims.
        new_photo_paths = save_uploaded_photos(policy_number, uploaded_photos)

        # -------------------------------------------------------------
        # AGENT 2: fraud check
        # -------------------------------------------------------------
        with st.spinner("Agent 2: checking photos for fraud signals..."):
            fraud_result = run_agent_2(
                policy_number=policy_number,
                new_photo_paths=new_photo_paths,
                accident_description=fields.get("accident_description", ""),
            )

        st.subheader("Agent 2 - Fraud check result")
        st.json(fraud_result)

        is_fraud = fraud_result["fraud_score"] >= FRAUD_THRESHOLD

        cost_result = None
        if is_fraud:
            st.error(
                f"Fraud score {fraud_result['fraud_score']:.2f} is above the "
                f"threshold ({FRAUD_THRESHOLD}). Stopping here - Agent 3 will "
                "NOT run. This claim is flagged for human review."
            )
            final_status = "flagged_fraud"
        else:
            st.success(
                f"Fraud score {fraud_result['fraud_score']:.2f} is below threshold. "
                "Proceeding to cost estimation."
            )
            # -------------------------------------------------------------
            # AGENT 3: cost estimate (only runs if not fraud)
            # -------------------------------------------------------------
            with st.spinner("Agent 3: estimating repair cost from photos..."):
                cost_result = run_agent_3(
                    photo_paths=new_photo_paths,
                    vehicle_make=fields.get("vehicle_make", ""),
                    vehicle_model=fields.get("vehicle_model", ""),
                )

            st.subheader("Agent 3 - Cost estimate result")
            st.json(cost_result)
            final_status = "approved"

        # -------------------------------------------------------------
        # AGENT 4: build the PDF report
        # -------------------------------------------------------------
        with st.spinner("Agent 4: building PDF report..."):
            pdf_path = run_agent_4(
                intake_result=intake_result,
                fraud_result=fraud_result,
                cost_result=cost_result,
                final_status=final_status,
            )

        # Save this claim to the database so it shows up in history next time
        insert_claim(
            policy_number=policy_number,
            customer_name=fields.get("customer_name", ""),
            claim_date=fields.get("accident_date", ""),
            claim_amount=cost_result["estimated_cost_usd"] if cost_result else 0.0,
            photo_path=str(PHOTO_STORAGE_ROOT / policy_number),
            status=final_status,
        )

        st.subheader("Final report")
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download PDF report",
                data=f.read(),
                file_name=pdf_path.name,
                mime="application/pdf",
            )


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    claim_processing_screen()
else:
    login_screen()

