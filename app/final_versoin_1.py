import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path

# Agents
from agent_1_intake import run_agent_1
from agent_2_fraud_check import run_agent_2
from agent_3_cost_estimate import run_agent_3
from agent_4_report import run_agent_4

# ====================================================
# PAGE CONFIG
# ====================================================
st.set_page_config(
    page_title="ClaimSphere AI",
    page_icon="🚗",
    layout="wide"
)

# ====================================================
# DATABASE CONFIG (from your original code)
# ====================================================
DB_CONFIG = {
    "host": "localhost",
    "port": "5433",
    "dbname": "claims_DB",
    "user": "postgres",
    "password": "Envy@2025"
}

PHOTO_STORAGE_ROOT = Path("data/photos")


# ====================================================
# DB CONNECTION
# ====================================================
def get_connection():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )


def get_claim_history(policy_number):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT id, policy_number, customer_name, claim_date,
               claim_amount, photo_path, status
        FROM claims
        WHERE policy_number = %s
        ORDER BY claim_date DESC
    """, (policy_number,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


def insert_claim(policy_number, customer_name, claim_date,
                 claim_amount, photo_path, status, drive_link=None):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO claims (
            policy_number,
            customer_name,
            claim_date,
            claim_amount,
            photo_path,
            status
        )
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        policy_number,
        customer_name,
        claim_date,
        claim_amount,
        photo_path,
        status
    ))

    conn.commit()
    cursor.close()
    conn.close()


# ====================================================
# LOGIN
# ====================================================
def login_page():
    st.title("🚗 ClaimSphere AI")
    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "adjuster" and password == "demo123":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")


# ====================================================
# PHOTO SAVE
# ====================================================
def save_uploaded_photos(policy_number, uploaded_files):
    folder = PHOTO_STORAGE_ROOT / policy_number
    folder.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for i, file in enumerate(uploaded_files):
        suffix = Path(file.name).suffix or ".jpg"
        path = folder / f"claim_{i}{suffix}"
        path.write_bytes(file.getvalue())
        saved_paths.append(path)

    return saved_paths


# ====================================================
# GOOGLE DRIVE (STUB)
# ====================================================
def upload_to_drive(policy_number, photo_paths):
    """
    Replace this later with real Google Drive API.
    For now we just simulate a folder URL.
    """
    return f"https://drive.google.com/drive/folders/{policy_number}_uploaded"


# ====================================================
# MAIN WORKFLOW
# ====================================================
def main_page():
    st.title("ClaimSphere AI")

    st.success("Logged in as Adjuster")

    # -----------------------------
    # STEP 1: POLICY SEARCH
    # -----------------------------
    st.header("1️⃣ Policy Lookup")

    policy_number = st.text_input("Enter Policy Number", placeholder="POL10001")

    history = None

    if st.button("Search Policy"):
        history = get_claim_history(policy_number)
        st.session_state.history = history

        if len(history) == 0:
            st.warning("No previous claims found.")
        else:
            st.subheader("Claim History")
            st.json(history)

    st.divider()

    # -----------------------------
    # STEP 2: NEW CLAIM ENTRY
    # -----------------------------
    st.header("2️⃣ New Claim Submission")

    claim_form_text = st.text_area(
        "Claim Form Details",
        height=160,
        placeholder="Enter accident description, vehicle details, etc."
    )

    uploaded_photos = st.file_uploader(
        "Upload Accident Photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    # -----------------------------
    # PROCESS PIPELINE
    # -----------------------------
    if st.button("Run AI Claim Pipeline", type="primary"):

        if not claim_form_text or not uploaded_photos:
            st.error("Please provide both claim form and photos.")
            return

        # -------------------------
        # AGENT 1
        # -------------------------
        with st.spinner("Agent 1 processing..."):
            intake_result = run_agent_1(claim_form_text)

        extracted = intake_result["extracted_fields"]
        policy = extracted.get("policy_number", policy_number)

        st.subheader("Agent 1 Output")
        st.json(intake_result)

        # Save photos locally
        saved_photos = save_uploaded_photos(policy, uploaded_photos)

        # -------------------------
        # AGENT 2
        # -------------------------
        with st.spinner("Agent 2 fraud detection..."):
            fraud_result = run_agent_2(
                policy_number=policy,
                new_photo_paths=saved_photos,
                accident_description=extracted.get("accident_description", "")
            )

        st.subheader("Agent 2 Output")
        st.json(fraud_result)

        FRAUD_THRESHOLD = 0.6
        fraud_score = fraud_result["fraud_score"]

        cost_result = None

        # -------------------------
        # DECISION GATE
        # -------------------------
        if fraud_score >= FRAUD_THRESHOLD:
            st.error("Fraud detected - stopping pipeline.")
            final_status = "flagged_fraud"

        else:
            st.success("No fraud detected - proceeding.")

            # -------------------------
            # AGENT 3
            # -------------------------
            with st.spinner("Agent 3 cost estimation..."):
                cost_result = run_agent_3(
                    photo_paths=saved_photos,
                    vehicle_make=extracted.get("vehicle_make", ""),
                    vehicle_model=extracted.get("vehicle_model", "")
                )

            st.subheader("Agent 3 Output")
            st.json(cost_result)

            final_status = "approved"

        # -------------------------
        # AGENT 4
        # -------------------------
        with st.spinner("Generating report..."):
            pdf_path = run_agent_4(
                intake_result=intake_result,
                fraud_result=fraud_result,
                cost_result=cost_result,
                final_status=final_status
            )

        st.success("Report generated")

        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download Report",
                f,
                file_name=pdf_path.name
            )

        # -------------------------
        # GOOGLE DRIVE UPLOAD
        # -------------------------
        drive_link = upload_to_drive(policy, saved_photos)

        # -------------------------
        # DATABASE INSERT
        # -------------------------
        insert_claim(
            policy_number=policy,
            customer_name=extracted.get("customer_name", ""),
            claim_date=extracted.get("accident_date", datetime.today().date()),
            claim_amount=cost_result["estimated_cost_usd"] if cost_result else 0,
            photo_path=drive_link,
            status=final_status
        )

        st.success("Claim stored in database & Drive linked")


# ====================================================
# SESSION STATE
# ====================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ====================================================
# ROUTING
# ====================================================
if st.session_state.logged_in:
    main_page()
else:
    login_page()