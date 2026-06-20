# Why this project skips LangGraph, RAG, vector databases, and Docker

If you've looked at other multi-agent AI projects, you've probably seen
these tools mentioned constantly. Here's the honest reasoning for why
this project doesn't use them, and when you actually would want to.

## LangGraph (workflow orchestration framework)

**What it's for:** Coordinating many agents with complex branching,
loops, retries, and the ability to pause execution for days and resume
later (for example, waiting on a human reviewer).

**Why this project doesn't need it:** There are 4 agents here, they run
once, in a fixed order, and the whole thing finishes in under a minute.
"Orchestration" in this case is just:

```python
result_1 = run_agent_1(...)
result_2 = run_agent_2(...)
if not fraud:
    result_3 = run_agent_3(...)
result_4 = run_agent_4(...)
```

That sequence of function calls **is** the orchestration. A framework
that exists to manage complex branching and persistence doesn't add
anything when your branching is one `if` statement and nothing needs to
survive a server restart.

**When you'd actually want it:** If you had 10+ agents, needed a claim
to sit "pending human review" for days while a checkpoint survives
server restarts, or needed automatic retries with complex state
recovery, LangGraph earns its place. That's the production version of
this project.

## RAG / Vector databases (ChromaDB, Pinecone, etc.)

**What it's for:** Searching through large amounts of *unstructured*
text - think hundreds of pages of policy documents where you need to
find the 2 relevant paragraphs out of 100 pages for a specific
question. This is the right tool when you can't fit all your reference
material into one prompt.

**Why this project doesn't need it:** Claim history and policy data
here are *structured* - a policy number, a date, an amount. That's a
database row, not a paragraph buried in a PDF. A SQL query
(`SELECT * FROM claims WHERE policy_number = ?`) finds the exact right
data instantly, with no risk of "almost matching" the wrong thing the
way semantic search sometimes can.

**When you'd actually want it:** If you added real policy *documents*
(coverage terms, exclusions, legal language spanning many pages) and
needed to ask "does this policy cover flood damage," that's
unstructured text search - that's when RAG over a vector database earns
its place.

## Docker

**What it's for:** Running multiple coordinated services (a database
server, a vector store, a backend API, a frontend) reliably across
different machines, so "it works on my machine" becomes "it works
everywhere."

**Why this project doesn't need it:** There's one Streamlit app and one
SQLite file. `streamlit run app/main_app.py` and `pip install -r
requirements.txt` is the entire deployment story. Adding Docker here
would mean writing and maintaining a Dockerfile and compose file for a
system that doesn't have multiple services to coordinate in the first
place.

**When you'd actually want it:** Once you introduce a real PostgreSQL
server, a separate vector database, and a separate backend API process
(the production version of this project), Docker Compose becomes the
right way to make sure all of those start up together and talk to each
other consistently.

## PostgreSQL vs SQLite

**What PostgreSQL is for:** A real database server that many users and
processes can read/write to at the same time, over a network.

**Why this project uses SQLite instead:** SQLite is a single file on
disk - no server, no credentials, no network configuration. For one
person testing this app on their own laptop, it's strictly simpler and
does the exact same job. The SQL queries in `utils/database.py` would
need only minor changes to point at PostgreSQL instead - the *shape* of
the solution doesn't change, just where the data physically lives.

**When you'd actually want it:** As soon as more than one person needs
to use the app at the same time, or it needs to run on a server that
multiple users hit concurrently.

## The general principle

Every one of these tools solves a *specific scaling problem*: many
agents, huge unstructured documents, many coordinated services, many
concurrent users. If you don't have that problem yet, adding the tool
doesn't make your project more "production-grade" - it just adds
surface area you have to learn, configure, and debug without getting
any benefit from it.

Build the simplest thing that solves your actual problem first. Add
each tool only once you hit the specific wall it's designed to solve.
That's also a great story to tell in an interview: *"I started simple,
identified the actual bottleneck, and added the right tool for that
specific problem"* is a much stronger narrative than *"I used every
trendy tool from the start."*
