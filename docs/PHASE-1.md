# Phase 1 — Agent + One-Command Ingest

**Goal:** Point the project at any company's PDF(s) with one command, then chat with an agent in the terminal that answers only about that company.

No FastAPI and no WhatsApp in this phase. Those come in Phase 2 and Phase 3.

## Deliverables

| # | File | What it does |
|---|------|--------------|
| 1 | `requirements.txt` | Pinned dependencies (langchain, langgraph, langchain-google-genai, chroma, pypdf, python-dotenv) |
| 2 | `.env.example` | `GOOGLE_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL` |
| 3 | `.gitignore` | Ignores `store/`, `.env`, `__pycache__/`, `.venv/` |
| 3b | `app/config.py` | Paths and model settings shared by ingest and the agent |
| 4 | `app/ingest.py` | CLI: `--company NAME` + PDF path(s) → load → chunk → embed → Chroma + `store/company.json` |
| 5 | `app/agent.py` | LangGraph agent: retrieve chunks → answer with strict prompt; memory per `thread_id` |
| 6 | `app/chat.py` | Small terminal chat loop to test the agent (also handy as a demo fallback) |

## Steps

1. **Setup:** create the venv, `requirements.txt`, `.env.example` and `.gitignore`.
2. **Ingest:**
   - Parse the args (`--company`, one or more PDF paths). Fail clearly if a file is missing or isn't a PDF.
   - Build the new store in a temp folder and swap it in only on success, so a failed run keeps the current company.
   - `pypdf` → `RecursiveCharacterTextSplitter` (≈1000 chars, 150 overlap).
   - Embed into Chroma, persisted in `store/chroma/`.
   - Write `store/company.json` with `{ "company": NAME, "files": [...], "ingested_at": ... }`.
   - Print a summary: company, number of pages, number of chunks.
3. **Agent:**
   - At startup, read `store/company.json`. If it's missing, show an error that says to run ingest first.
   - Build the chat model with `init_chat_model(LLM_MODEL)`, so the provider comes from `.env`.
   - Graph: `retrieve` (top ~4 chunks for the latest question) → `answer` (system prompt + chunks + history).
   - Memory: `InMemorySaver` checkpointer, `thread_id` per user.
4. **System prompt:** follows the rules in PROJECT-CONTEXT.md:
   - "You are the assistant for {company}."
   - Answer only from the provided context.
   - Politely refuse off-topic questions.
   - If the answer isn't in the context, say so and suggest contacting {company}.
   - Keep replies short and chat-style.
5. **Terminal chat:** `python -m app.chat` runs a question/answer loop with one fixed `thread_id`. Type `exit` to quit.
6. **Test with 2 different PDFs** using the checklist below.

## Done When (acceptance checklist)

- [ ] `python -m app.ingest --company "Company X" x.pdf` runs and prints a summary.
- [ ] The agent introduces itself as Company X's assistant.
- [ ] It answers a question whose answer is in the PDF correctly.
- [ ] It handles a follow-up question that relies on the previous message (memory works).
- [ ] It says it doesn't know when asked something about the company that isn't in the PDF, and doesn't make anything up.
- [ ] It politely refuses an off-topic question (e.g. "write me a poem", "who won the World Cup?").
- [ ] After re-running ingest with Company Y's PDF, the agent is Company Y's assistant and knows nothing about Company X.
- [ ] No company name or PDF appears anywhere in the code or the git history.

## Models

Chat: `google_genai:gemini-3.5-flash-lite`. Embeddings: `gemini-embedding-001`. Both are set in `.env`.

## Not in Phase 1

FastAPI endpoint, WhatsApp, persistent memory (SQLite/Postgres), several companies loaded at once, non-PDF data sources, deployment.
