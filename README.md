# ClaimSphere AI (Simple Edition)

A multi-agent AI system that processes vehicle insurance claims end to end:
reads the claim form, checks claim history, detects photo-based fraud, estimates
repair cost, and produces a downloadable PDF report.

This is the **simplified, beginner-friendly version** of the project. It
intentionally avoids heavy frameworks (LangGraph, vector databases, Docker)
so that every line of code is something you can read and understand. See
[`docs/why-no-frameworks.md`](docs/why-no-frameworks.md) for the reasoning.

## How it works

```
Login → Upload claim form + photos
            │
            ▼
   Agent 1: read form + check claim history (database)
            │
            ▼
   Agent 2: fraud check (compares new photo vs old photos)
            │
       ┌────┴────┐
   fraud found   no fraud
       │             │
   stop, flag    Agent 3: estimate repair cost from photos
       │             │
       └──────┬──────┘
              ▼
   Agent 4: build PDF report → download
```

There are 4 "agents." Each one is just a Python function. There is no
orchestration framework - `app/main_app.py` calls them in order, the same
way you'd call any other function, passing each one's output dict into
the next.

| Agent | File | What it does | Needs AI? |
|---|---|---|---|
| 1. Intake | `app/agent_1_intake.py` | Extracts name/policy number/etc from the form text, looks up past claims in the database | Yes - text |
| 2. Fraud check | `app/agent_2_fraud_check.py` | Compares the new photo against any previously stored photo for that policy number | Yes - vision |
| 3. Cost estimate | `app/agent_3_cost_estimate.py` | Reads damage severity from photos, estimates repair cost | Yes - vision |
| 4. Report | `app/agent_4_report.py` | Combines the other 3 agents' outputs into a PDF | No - just formatting |

Agent 3 only runs if Agent 2 does not flag fraud. That logic is a plain
`if` statement in `main_app.py` - see [`docs/architecture.md`](docs/architecture.md)
for the full walkthrough.

## Project structure

```
claimsphere-simple/
├── app/
│   ├── main_app.py              # Streamlit app + orchestration (the "graph")
│   ├── agent_1_intake.py        # form extraction + history lookup
│   ├── agent_2_fraud_check.py   # photo-vs-photo fraud detection
│   ├── agent_3_cost_estimate.py # repair cost estimation
│   └── agent_4_report.py        # PDF generation
├── utils/
│   └── database.py              # SQLite setup + queries (the one table we need)
├── data/                        # created automatically at runtime
│   ├── claims.db                # SQLite database file
│   ├── photos/<policy_number>/  # uploaded photos, organized by policy
│   └── reports/                 # generated PDF reports
├── docs/
│   ├── architecture.md          # why each piece exists, in plain language
│   └── why-no-frameworks.md     # why this skips LangGraph/RAG/Docker
├── requirements.txt
├── .env.example
└── README.md
```

## Running it yourself

**1. Clone and install dependencies**

```bash
git clone <your-repo-url>
cd claimsphere-simple
pip install -r requirements.txt
```

**2. Set your Anthropic API key**

```bash
cp .env.example .env
# then edit .env and paste your real key, OR just export it directly:
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get a key at [console.anthropic.com](https://console.anthropic.com/).

**3. Run the app**

```bash
streamlit run app/main_app.py
```

**4. Log in**

The demo login is hardcoded for simplicity:
- Username: `adjuster`
- Password: `demo123`

(See the warning in `main_app.py` - replace this with real auth before
using this anywhere beyond your own machine.)

**5. Try it**

The database is pre-seeded with a few sample policies so you have
something to test fraud detection against. Try submitting a claim for
`POL-1001` twice with similar photos to see the fraud check in action,
and `POL-3003` for a clean first-time claim.

## Sample claim form text to paste in

```
Name: Jane Doe
Policy Number: POL-1001
Vehicle: 2020 Toyota Camry
Accident Date: 2026-06-10
Description: Rear-ended at a stop light, bumper and trunk damaged.
```

## What this project deliberately leaves out (and why)

- **No LangGraph** - 4 agents running once in sequence don't need a
  workflow engine. Plain function calls are the workflow.
- **No vector database / RAG** - there's no large unstructured document
  to search through. Policy and claim data are structured rows, so a
  normal SQL query is the right tool, not semantic search.
- **No Docker** - one Streamlit app plus one SQLite file needs no
  container orchestration.
- **No PostgreSQL** - SQLite is a single file, zero setup, perfect for
  a single-user demo. Swapping to PostgreSQL later only requires
  changing `utils/database.py` - the rest of the app doesn't change.

Full reasoning in [`docs/why-no-frameworks.md`](docs/why-no-frameworks.md).

## Known limitations (this is a learning project, not production)

- Login is hardcoded, not real authentication.
- Cost estimates come from the model's general knowledge, not a real
  parts/labor price list.
- Photos are stored on local disk, not cloud storage - fine for a demo,
  but won't survive redeploying the app fresh.
- No automated test suite (the code was manually verified during
  development - see commit history).

## License

MIT - use this however you'd like.
