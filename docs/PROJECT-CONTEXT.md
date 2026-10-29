# Project Context — demo.ai

## Goal

A **demo** company-assistant agent that can become the assistant for **any company** with one command. It answers questions **only about that company**, using that company's PDF(s). Later it will be connected to WhatsApp so customers get instant replies.

### Company-agnostic by design

The project is used as a sales/demo tool. When we demo to Company X, we use Company X's PDF. When we demo to Company Y, we use Company Y's PDF.

- No company name, data or PDF is hardcoded or committed to the repo.
- One command switches the agent to a new company:

  ```bash
  python -m app.ingest --company "Company X" path/to/companyx.pdf [more.pdf ...]
  ```

- Running ingest **replaces** the active knowledge base. Only one company is active at a time.
- The company name is saved next to the vector store. The agent reads it at startup and uses it in its system prompt ("You are the assistant for {company}…").

## Scope & Phases

| Phase | What | Status |
|-------|------|--------|
| 1 | Agent + one-command ingest of any company's PDF(s); answers grounded only in that data ([plan](PHASE-1.md)) | Done |
| 2 | Expose agent over HTTP with FastAPI (`POST /chat`) for local testing ([plan](PHASE-2.md)) | Done |
| 3 | WhatsApp integration (webhook → agent → reply) ([plan](PHASE-3.md)) | **Current** |
| 4 | Deployment | Later |

WhatsApp details (number, Meta account, provider) are covered in [PHASE-3.md](PHASE-3.md).

## Core Behaviour Rules

1. Answer **only** from the company data. Do not use general knowledge to fill gaps.
2. If the question is unrelated to the company, politely decline and steer back to company topics.
3. If the answer is not in the data, say so honestly and suggest contacting the company. Never invent prices, policies, dates or contact details.
4. Replies are short and conversational. They are meant for chat and will later be sent on WhatsApp.
5. Remember the conversation per user (follow-up questions like "and how much does it cost?" must work).

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.11+ | |
| API | FastAPI | Phase 2 onward |
| Agent framework | **LangGraph** (+ LangChain components) | See decision below |
| PDF loading | `pypdf` (wrapped into LangChain `Document`s) | `langchain-community` loaders are deprecated |
| Chunking | `RecursiveCharacterTextSplitter` | |
| Vector store | Chroma (local, persisted to disk) | No external DB needed |
| LLM | **Google Gemini: `gemini-3.5-flash-lite`** | Through `init_chat_model`, so switching only needs a `.env` change |
| Embeddings | **Google `gemini-embedding-001`** | Changing it requires re-running ingest |

### Why LangGraph (with LangChain parts)

- **LangChain** supplies the building blocks: PDF loader, text splitter, vector store and a provider-agnostic chat model (`init_chat_model`). That matters so the model can be changed through config.
- **LangGraph** runs the agent flow. Its built-in checkpointer gives **per-user conversation memory keyed by a `thread_id`**. Later that ID will be the WhatsApp phone number, so we don't need to build memory ourselves.
- LangGraph also makes the later additions simple: human handoff, extra tools (e.g. order lookup) and guardrail steps.
- Plain LangChain alone would work for single-turn Q&A, but it would need hand-rolled memory as soon as we add chat.

## Agent Flow (Phase 1)

```
Ingest (once per company, one command):
  --company "X" + PDF path(s) → wipe old store → load → split into chunks
    → embed → Chroma (persisted in store/) + save company name (store/company.json)

Per question (agentic RAG):
  user message + thread_id
    → LLM (strict system prompt + chat history) decides:
        greeting / off-topic → reply directly (no search)
        company question     → calls search_company_info(query)
                               → embed query → Chroma top 5 → best 3 (score ≥ 0.4) → back to LLM
    → answer only from search results (or "don't have that info")
```

## Planned Project Layout

```
demo.ai/
├── CLAUDE.md
├── README.md
├── docs/PROJECT-CONTEXT.md
├── store/              # generated: Chroma DB + company.json (gitignored)
├── app/
│   ├── config.py       # paths + model settings from .env
│   ├── ingest.py       # CLI: --company NAME + PDF path(s) → replaces vector store
│   ├── agent.py        # LangGraph agent (retrieve → answer, with memory)
│   ├── chat.py         # terminal chat (Phase 1 demo)
│   └── main.py         # FastAPI app (Phase 2)
├── .env.example        # model/provider keys and settings
└── requirements.txt
```

## Open Decisions

- [x] LLM: Gemini `gemini-3.5-flash-lite` (decided 2026-10-29)
- [x] Embeddings: `gemini-embedding-001` (decided 2026-10-29)
- [ ] Reply language(s): English only, or also Hindi/other languages?
- [ ] Memory storage: in-memory for now; a persistent checkpointer (SQLite/Postgres) before production

## Out of Scope (for now)

WhatsApp setup, deployment, admin UI, analytics, multiple data sources besides PDFs, and several companies active at the same time (re-run ingest to switch).
