# Architecture, explained in plain language

This doc walks through every piece of the system and explains *why* it
exists, written for someone who is comfortable with Python but new to
building AI agent systems.

## What does "agent" mean here?

In this project, an "agent" is just a Python function that:
1. Takes some input (text, images, or both)
2. Optionally calls Claude's API to reason about that input
3. Optionally queries the database
4. Returns a dictionary with its results

That's the whole definition. There's no special "agent class," no
autonomous decision-making loop, no agent "deciding" what to do next on
its own. Agent 1 always runs first, then Agent 2, then conditionally
Agent 3, then Agent 4. The order is fixed and written directly in
`main_app.py`.

## Why a dictionary is "the state"

You'll hear terms like "state management" in more advanced agent
frameworks. All that means here is: each agent returns a dict, and you
pass that dict (or pieces of it) into the next agent's function call.

```python
intake_result = run_agent_1(claim_form_text)
fraud_result = run_agent_2(
    policy_number=intake_result["extracted_fields"]["policy_number"],
    ...
)
```

`intake_result` flowing into `run_agent_2` IS the state being passed
between agents. There's no hidden machinery - it's just a Python
function argument.

## Why each agent calls Claude (or doesn't)

| Agent | Calls Claude? | Why |
|---|---|---|
| 1 | Yes, text only | Turning messy free-text into structured fields (name, policy number, etc) is exactly what an LLM is good at - it understands varied phrasing a fixed regex couldn't. |
| 2 | Yes, with images | Comparing two photos for similarity/reuse and checking if damage matches a description requires actually looking at the images - this is a vision task. |
| 3 | Yes, with images | Estimating damage severity and cost also requires looking at the photos. |
| 4 | No | Building a PDF from data you already have is pure formatting - no reasoning needed, so no AI call needed. |

A good rule of thumb: **only call the LLM when the task genuinely
requires language understanding or visual understanding.** Don't reach
for an AI call to do something a normal `if` statement or string
formatting can do (like Agent 4).

## Why one Claude model handles both text and images

You might expect to need a separate "vision model" and "language
model." You don't - Claude (and GPT-4o) can accept both text and images
in the *same* API call. That's why Agent 1 (text-only) and Agents 2/3
(text + images) all just call `client.messages.create(...)` - the only
difference is what's in the `content` list of the message.

This is the same thing as uploading a photo to Claude or ChatGPT in a
regular chat and asking a question about it - you're doing that exact
same operation through code instead of a chat window.

## Why the database is one table

The database's only job in this project is answering: *"has this policy
number claimed before, how much, when, any past fraud flags?"* One
table with one row per claim answers that completely:

```sql
claims (id, policy_number, customer_name, claim_date, claim_amount, photo_path, status)
```

You don't need separate tables for "customers" and "policies" unless
you're tracking a lot more about each (multiple vehicles per policy,
billing info, etc). Start with the smallest schema that answers your
actual question, and only add tables when you have a concrete new
question that requires one.

## Why fraud detection compares photos, not just descriptions

The interesting fraud signal in this project is: *did the customer
upload the same photo (or a lightly edited version) that they used in
a previous claim?* That's a strong reuse signal that text alone can't
catch. Agent 2 fetches whatever photo was saved from this policy's most
recent claim and hands both images to Claude in a single message,
asking it to compare them directly - this is the same workflow as
manually uploading two photos to a chat interface and asking "are these
the same?"

## Why Agent 3 is gated behind Agent 2

Estimating repair cost on photos that may be fraudulent wastes an API
call and could produce a misleadingly confident-looking cost estimate
for a claim that shouldn't be paid out at all. The gate is a single
`if` statement in `main_app.py`:

```python
if fraud_result["fraud_score"] >= FRAUD_THRESHOLD:
    final_status = "flagged_fraud"
    # Agent 3 never runs
else:
    cost_result = run_agent_3(...)
    final_status = "approved"
```

No special "routing" tool is needed for this - conditional branching in
plain Python is the same concept as a "conditional edge" in a workflow
framework, just without the framework.

## Where this would need to change for production use

This project optimizes for being understandable and runnable in a
week. If you wanted to actually run this for real customers, you'd
want to revisit:

- **Auth**: replace the hardcoded login with a real provider.
- **Storage**: move photos from local disk to cloud storage (S3, GCS,
  or Google Drive if you want that specific integration) so they
  survive redeployments and can scale beyond one machine.
- **Concurrency**: SQLite handles one writer at a time well, but many
  simultaneous adjusters submitting claims would need PostgreSQL.
- **Audit trail**: for a real insurance product, you'd want to log
  every agent's exact input/output for compliance, not just the final
  PDF.
- **Confidence-based human review queue**: right now fraud-flagged
  claims just stop. A real system would route them into a queue an
  adjuster can review and resolve.

These are exactly the upgrades a more advanced version of this project
(using LangGraph, a proper database schema, and cloud storage) is built
to handle - but they're additions, not prerequisites, to understanding
how the core multi-agent flow works.
