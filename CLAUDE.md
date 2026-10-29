# CLAUDE.md

Demo company Q&A agent. It works for **any company**: one ingest command loads that company's PDF(s), and the agent then answers only about that company. Will be connected to WhatsApp later.
Full context, phases and decisions: **[docs/PROJECT-CONTEXT.md](docs/PROJECT-CONTEXT.md)**. Read it before starting work.

## Stack

Python 3.11+, FastAPI, LangGraph + LangChain components, Chroma (local vector store).
The LLM and embedding model are **not decided yet**, so never hardcode a provider. Create models through `init_chat_model` and pick the provider and model from env config.

## Rules

- **Company-agnostic:** never hardcode a company name, data or PDF path. The company comes only from the ingest command (`--company` + PDF paths), which replaces the active store in `store/` (gitignored). PDFs are never committed.
- Work on the current phase only (see the phase table in PROJECT-CONTEXT.md). Don't build WhatsApp, deployment or extras before they're asked for.
- The agent must answer only from the company data and politely refuse off-topic questions. Never let it invent prices, policies or contact info.
- Per-user memory uses the LangGraph checkpointer with `thread_id` (later this will be the WhatsApp phone number).
- Secrets go in `.env` (never committed). Keep `.env.example` up to date.
- Keep it simple: few files, no abstractions without a second use case.
- When a decision in "Open Decisions" gets made, update PROJECT-CONTEXT.md.

## Commands

```bash
python -m app.ingest --company "Company X" path/to/companyx.pdf   # switch agent to Company X (planned)
```

_Install, run and test commands will be added once code exists._
