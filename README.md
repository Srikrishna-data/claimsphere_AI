# ClaimSphere AI

A multi-agent AI system that automates vehicle insurance claim processing end to end.
The adjuster logs in, enters a policy number, types the claim details, uploads accident
photos — and the system handles the rest: reads the form, checks fraud, estimates repair
cost, and generates a downloadable PDF report.

---

## What it actually does

```
Login
  │
  ▼
Enter Policy Number → pulls full claim history from PostgreSQL
  │
  ▼
Type claim details + upload accident photos
  │
  ▼
Agent 1 — reads the claim form text, extracts structured fields,
          cross-checks claim history from the database
  │
  ▼
Agent 2 — compares the new uploaded photo against the previously
          stored photo for this policy (fraud detection)
  │
  ┌──────────────┴──────────────┐
fraud detected              no fraud
  │                             │
pipeline stops            Agent 3 — estimates repair cost
  │                       from the damage photos
  └──────────┬────────────┘
             ▼
Agent 4 — generates a PDF report with the full decision
  │
  ▼
Download PDF + claim row saved to PostgreSQL
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| UI | Streamlit | Fast to build, easy to demo |
| Agent 1 (text) | Groq — LLaMA 3.3 70B | Free tier, fast inference, good at structured extraction |
| Agent 2 & 3 (vision) | Gemini Vision | Multimodal — can compare and analyze photos |
| Database | PostgreSQL | Stores claim history per policy number |
| Photo storage | Local folder per policy number | Organized by policy, used for fraud comparison |
| PDF generation | fpdf2 | No AI needed here — just formatting |

No LangGraph. No LangChain. No vector database. No Docker.
Each agent is a plain Python function. The "pipeline" is just calling them in order.

---

## Project structure

```
claimsphere-ai/
├── final_version_1.py       # Streamlit app — login, UI, pipeline orchestration
├── agent_1_intake.py        # Groq: extracts fields from claim text + DB history lookup
├── agent_2_fraud_check.py   # Gemini Vision: compares new photo vs stored photo
├── agent_3_cost_estimate.py # Gemini Vision: reads damage and estimates repair cost
├── agent_4_report.py        # fpdf2: builds the PDF report, no AI call
├── database.py              # PostgreSQL connection + queries (get history, insert claim)
├── data/
│   ├── photos/              # one subfolder per policy number, stores uploaded photos
│   └── reports/             # generated PDF reports saved here
└── requirements.txt
```

---

## How to run it

**1. Clone the repo**

```bash
git clone https://github.com/<your-username>/claimsphere-ai
cd claimsphere-ai
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Set up your API keys**

You need two API keys — both have free tiers:

```bash
# Groq (Agent 1) — get from https://console.groq.com
export GROQ_API_KEY=your_groq_key_here

# Gemini (Agents 2 & 3) — get from https://aistudio.google.com
export GOOGLE_API_KEY=your_gemini_key_here
```

**4. Set up PostgreSQL**

Make sure PostgreSQL is running and create the claims table:

```sql
CREATE TABLE claims (
    id            SERIAL PRIMARY KEY,
    policy_number TEXT,
    customer_name TEXT,
    claim_date    TEXT,
    claim_amount  FLOAT,
    photo_path    TEXT,
    status        TEXT
);
```

Update the `DB_CONFIG` in `final_version_1.py` and `database.py` with
your host, port, database name, and credentials.

**5. Run the app**

```bash
streamlit run final_version_1.py
```

**6. Log in**

```
Username: adjuster
Password: demo123
```

---

## How to test it

**Test the fraud detection (the interesting demo):**
1. Search a policy number that already has a past claim with a photo stored
2. Upload the same photo again as the "new" accident photo
3. Agent 2 will flag it as fraud, Agent 3 will not run

**Test the clean approval path:**
1. Use a policy number with no prior claims (or use a clearly different photo)
2. All 3 agents run, cost estimate appears, PDF downloads

---

## Why no LangChain, LangGraph, or vector database

These are real tools that solve real problems — just not the ones this project has.

- **LangChain / LangGraph** are for complex multi-step agent loops, branching
  workflows, and state that needs to survive crashes. Here, 4 agents run once
  in a fixed sequence. A plain function call chain does the same job without
  the overhead.

- **Vector databases (ChromaDB, Pinecone)** are for searching large unstructured
  documents — like finding the 3 relevant paragraphs from a 200-page policy PDF.
  Here, the claim data is structured rows in a table. A SQL query is the right
  tool for structured data.

- **Docker** makes sense when you have multiple services to coordinate. One
  Streamlit app and one Postgres instance don't need container orchestration.

---

## Planned upgrades (advanced roadmap)

- [ ] Upload PDF claim form instead of typing text — Agent 1 reads it directly
- [ ] Google Drive integration — photos uploaded to a per-policy Drive folder
      instead of local disk, persists across deployments
- [ ] LangGraph orchestration — adds proper state management, retries, and
      a human-in-the-loop review queue for flagged claims
- [ ] RAG over policy documents — adjuster uploads the policy PDF, Agent 1
      checks whether the claimed damage is actually covered
- [ ] Real repair cost lookup — replace model estimates with a parts/labor
      pricing API for accurate payout figures
- [ ] Email the report — send the PDF decision directly to the customer

---

## License

MIT — use this however you like.
