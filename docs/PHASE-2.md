# Phase 2 — FastAPI `POST /chat`

**Goal:** Put the Phase 1 agent behind a small HTTP API so anything (curl, a web page, and in Phase 3 the WhatsApp webhook) can chat with it.

The agent itself does not change. This phase only adds a thin web layer on top of `load_agent()` / `ask()`. No WhatsApp yet.

## Deliverables

| # | File | What it does |
|---|------|--------------|
| 1 | `requirements.txt` | Add `fastapi` and `uvicorn` (pinned) |
| 2 | `app/main.py` | FastAPI app: loads the agent once at startup, exposes `POST /chat` and `GET /health` |
| 3 | `CLAUDE.md`, `README.md` | Add the command that starts the server |

## API

**`POST /chat`**

```json
// request
{ "thread_id": "user-123", "message": "When was the company founded?" }

// response 200
{ "reply": "Elemensis Softech LLP was officially incorporated on January 17, 2018." }
```

- `thread_id` (1–100 chars): one per conversation. The agent remembers history per `thread_id`. In Phase 3 this will be the customer's WhatsApp number.
- `message` (1–2000 chars): the customer's text. Empty or oversized input is rejected with `422` before it reaches the agent or Gemini.

**`GET /health`** → `{ "status": "ok", "company": "<active company>" }`. Shows which company is loaded.

FastAPI also serves interactive docs at **`/docs`**, so you can try the API in a browser without writing any client.

## Steps

1. Add `fastapi` and `uvicorn` to `requirements.txt` and install them.
2. Write `app/main.py`:
   - Call `load_agent()` once when the server starts. If nothing is ingested, the server exits with the same "run ingest first" hint as the terminal chat.
   - Validate the request body with a Pydantic model (length limits above).
   - `POST /chat` calls `ask(agent, message, thread_id)` and returns `{reply}`.
3. Start the server: `.venv/bin/uvicorn app.main:app --reload`.
4. Test with curl and `/docs` using the checklist below.

## Done When (acceptance checklist)

- [x] `uvicorn app.main:app` starts and `GET /health` shows the active company.
- [x] `POST /chat` answers a question from the PDF correctly.
- [x] Two requests with the **same** `thread_id` keep context (a follow-up works).
- [x] Two **different** `thread_id`s don't see each other's conversation.
- [x] Off-topic message → polite refusal; greeting → no search (check the `[search]` log).
- [x] Empty `message` → `422`, without calling Gemini.
- [ ] Re-running ingest for another company and restarting the server switches the company.

## Notes

- Memory is still in RAM (`InMemorySaver`): restarting the server forgets all chats. Persistent memory is a later decision (see Open Decisions in PROJECT-CONTEXT.md).
- The `[search]` / `[rag]` debug lines now print in the server log.
- After re-running ingest, restart the server (`--reload` only watches code, not `store/`).

## Not in Phase 2

WhatsApp webhook, authentication / API keys, rate limiting, streaming replies, persistent memory, deployment.
