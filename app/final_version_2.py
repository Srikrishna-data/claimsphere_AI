import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from pathlib import Path

from streamlit import cursor

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
    # Convert empty strings to None (NULL in Postgres)
    customer_name = customer_name or None
    claim_date = claim_date or None
    policy_number = policy_number or None
    photo_path = photo_path or None
    status = status or None
    claim_amount = claim_amount if claim_amount is not None else 0


    cursor.execute("""
        INSERT INTO claims (
        policy_number, customer_name, claim_date,
        claim_amount, photo_path, status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (policy_number, customer_name, claim_date,
        claim_amount, photo_path, status))

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
        if username == "Sri_krishna" and password == "demo123":
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
    return f"https://drive.google.com/drive/folders/{policy_number}_uploaded"


# ====================================================
# MAIN WORKFLOW
# ====================================================
def main_page():
    st.title("🚗 ClaimSphere AI")
    st.success("Logged in as Sri_krishna")

    # -----------------------------
    # STEP 1: POLICY SEARCH
    # -----------------------------
    st.header("1️⃣ Policy Lookup")

    policy_number = st.text_input("Enter Policy Number", placeholder="POL10001")

    if st.button("Search Policy"):
        history = get_claim_history(policy_number)
        st.session_state.history = history

        if len(history) == 0:
            st.warning("No previous claims found for this policy.")
        else:
            st.subheader("Claim History")

            # ── CHANGED: table view instead of st.json ──
            for row in history:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"**Date**\n\n{row['claim_date']}")
                    c2.markdown(f"**Amount**\n\n${float(row['claim_amount']):,.2f}")
                    c3.markdown(f"**Status**\n\n{row['status'].upper()}")
                    c4.markdown(f"**Claim ID**\n\n#{row['id']}")

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

    if uploaded_photos:
        cols = st.columns(min(len(uploaded_photos), 4))
        for i, photo in enumerate(uploaded_photos):
            with cols[i % 4]:
                st.image(photo, use_container_width=True, caption=photo.name)

    # -----------------------------
    # PROCESS PIPELINE
    # -----------------------------
    if st.button("Run AI Claim Pipeline", type="primary"):

        if not claim_form_text or not uploaded_photos:
            st.error("Please provide both claim form details and photos.")
            return

        # -------------------------
        # AGENT 1
        # -------------------------
        with st.spinner("Agent 1: Reading claim form and checking history..."):
            intake_result = run_agent_1(claim_form_text)

        extracted = intake_result["extracted_fields"]
        history   = intake_result["claim_history"]
        policy    = extracted.get("policy_number", policy_number)

        # ── CHANGED: cards instead of st.json ──
        st.subheader("Agent 1 — Claim Intake")
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.markdown("**Extracted details**")
                st.write(f"👤 **Name:** {extracted.get('customer_name', '-')}")
                st.write(f"📋 **Policy:** {extracted.get('policy_number', '-')}")
                st.write(f"🚗 **Vehicle:** {extracted.get('vehicle_make', '')} {extracted.get('vehicle_model', '')}")
                st.write(f"📅 **Accident Date:** {extracted.get('accident_date', '-')}")
                st.write(f"📝 **Description:** {extracted.get('accident_description', '-')}")

        with col2:
            with st.container(border=True):
                st.markdown("**Claim History from Database**")
                st.metric("Past Claims", history["past_claim_count"])
                st.metric("Total Paid Out", f"${history['total_past_payout']:,.2f}")
                fraud_flag = history.get("has_fraud_flag_history", False)
                st.metric("Prior Fraud Flags", "Yes" if fraud_flag else "None")
                if history.get("claims"):
                    last = history["claims"][0]
                    st.caption(f"Last claim: {last.get('claim_date','')}  |  ${float(last.get('claim_amount',0)):,.2f}  |  {last.get('status','')}")

        # Save photos locally (unchanged)
        saved_photos = save_uploaded_photos(policy, uploaded_photos)

        # -------------------------
        # AGENT 2
        # -------------------------
        with st.spinner("Agent 2: Running fraud detection on photos..."):
            fraud_result = run_agent_2(
                policy_number=policy,
                new_photo_paths=saved_photos,
                accident_description=extracted.get("accident_description", "")
            )

        FRAUD_THRESHOLD = 0.6
        fraud_score = fraud_result["fraud_score"]

        # ── CHANGED: visual fraud score instead of st.json ──
        st.subheader("Agent 2 — Fraud Detection")
        with st.container(border=True):
            fa, fb = st.columns([1, 2])
            with fa:
                st.metric(
                    "Fraud Score",
                    f"{fraud_score:.2f} / 1.00",
                    delta="HIGH RISK" if fraud_score >= FRAUD_THRESHOLD else "LOW RISK",
                    delta_color="inverse" if fraud_score >= FRAUD_THRESHOLD else "normal"
                )
            with fb:
                st.write(f"**Reasoning:** {fraud_result.get('reason', '-')}")
                compared = fraud_result.get("compared_against_history", False)
                if compared:
                    st.caption("Compared against historical photo from storage.")
                else:
                    st.caption("No historical photo found — first claim for this policy.")

        cost_result = None

        # -------------------------
        # DECISION GATE (unchanged)
        # -------------------------
        if fraud_score >= FRAUD_THRESHOLD:
            st.error("Fraud detected — pipeline stopped. Claim flagged for manual review.")
            final_status = "flagged_fraud"

        else:
            st.success("No fraud detected — proceeding to cost estimation.")

            # -------------------------
            # AGENT 3
            # -------------------------
            with st.spinner("Agent 3: Estimating repair cost from photos..."):
                cost_result = run_agent_3(
                    photo_paths=saved_photos,
                    vehicle_make=extracted.get("vehicle_make", ""),
                    vehicle_model=extracted.get("vehicle_model", "")
                )

            # ── CHANGED: cards instead of st.json ──
            st.subheader("Agent 3 — Repair Cost Estimate")
            with st.container(border=True):
                st.metric(
                    "Estimated Repair Cost",
                    f"${cost_result.get('estimated_cost_usd', 0):,.2f}"
                )
                st.write(f"**Notes:** {cost_result.get('notes', '-')}")
                st.markdown("**Damaged Parts:**")
                part_cols = st.columns(min(len(cost_result.get("damaged_parts", [])), 3) or 1)
                for i, part in enumerate(cost_result.get("damaged_parts", [])):
                    with part_cols[i % len(part_cols)]:
                        severity = part.get("severity", "")
                        color = {"minor": "🟡", "moderate": "🟠", "severe": "🔴"}.get(severity, "⚪")
                        st.write(f"{color} **{part.get('part', '')}**")
                        st.caption(severity)

            final_status = "approved"

        # -------------------------
        # AGENT 4 (unchanged logic)
        # -------------------------
        with st.spinner("Agent 4: Generating PDF report..."):
            pdf_path = run_agent_4(
                intake_result=intake_result,
                fraud_result=fraud_result,
                cost_result=cost_result,
                final_status=final_status
            )

        st.divider()
        st.subheader("Final Decision")

        if final_status == "approved":
            st.success("Decision: APPROVED")
        else:
            st.error("Decision: FLAGGED FOR REVIEW")

        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download Claim Report PDF",
                f,
                file_name=pdf_path.name,
                mime="application/pdf",
                use_container_width=True
            )

        # GOOGLE DRIVE UPLOAD (unchanged)
        drive_link = upload_to_drive(policy, saved_photos)

        # DATABASE INSERT (unchanged)
        insert_claim(
            policy_number=policy,
            customer_name=extracted.get("customer_name", ""),
            claim_date=extracted.get("accident_date", datetime.today().date()),
            claim_amount=cost_result["estimated_cost_usd"] if cost_result else 0,
            photo_path=drive_link,
            status=final_status
        )

        st.success("Claim saved to database and Drive link stored.")

    st.divider()
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()


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