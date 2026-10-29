# Phase 3 — WhatsApp

**Goal:** A customer sends a WhatsApp message to the business number and gets the agent's reply within a few seconds.

The agent does not change. This phase adds a WhatsApp webhook next to `POST /chat` that calls the same `ask()`, with the customer's phone number as the `thread_id`, so every customer gets their own memory.

## How it works

```
Customer's WhatsApp
   │  message
   ▼
Meta WhatsApp Cloud API ──POST /webhook──▶ our FastAPI app (public URL via ngrok)
                                              │ 1. check signature, reply 200 at once
                                              │ 2. in background: ask(agent, text, thread_id=phone)
                                              ▼
Meta Graph API  ◀──POST /{phone_number_id}/messages── reply text
   │
   ▼
Customer's WhatsApp
```

## Provider decision

| Option | Pros | Cons |
|---|---|---|
| **Meta WhatsApp Cloud API (recommended)** | Official, free test number, no middleman fee, same setup goes to production | Meta developer app setup takes ~30 min; webhook needs signature check |
| Twilio WhatsApp | Sandbox ready in minutes, simple form-encoded webhook | Extra per-message fee, sandbox users must "join" with a code, moving to production still needs Meta approval |

Recommendation: **Meta Cloud API directly**. It's the path a real business number ends up on anyway.

## Setup (one time, done by us in the Meta dashboard)

1. Create a Meta developer app (type **Business**) and add the **WhatsApp** product.
2. Meta gives a **test phone number** and a **temporary access token**. Note the **Phone number ID**.
3. Add up to 5 recipient numbers (our own phones) that are allowed to message the test number.
4. Start the server and expose it: `ngrok http 8000` → copy the `https://….ngrok-free.app` URL.
5. In WhatsApp → Configuration, set the callback URL to `https://…/webhook` and the verify token to our `WHATSAPP_VERIFY_TOKEN`, then subscribe to the **messages** field.

## Deliverables

| # | File | What it does |
|---|------|--------------|
| 1 | `.env.example` | Add `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_API_VERSION` |
| 2 | `app/config.py` | Read the WhatsApp settings from `.env` |
| 3 | `app/main.py` | `GET /webhook` (Meta's verification handshake) and `POST /webhook` (incoming messages → agent → reply) |
| 4 | `CLAUDE.md`, `README.md` | How to run with ngrok |

No new dependency: `httpx` is already installed (via langchain/chroma) and is used to call the Graph API.

## Webhook behaviour

- **`GET /webhook`**: if `hub.mode == "subscribe"` and `hub.verify_token` matches ours, return `hub.challenge` as plain text; otherwise `403`.
- **`POST /webhook`**:
  1. Verify the `X-Hub-Signature-256` header (HMAC-SHA256 of the raw body with `WHATSAPP_APP_SECRET`). Wrong or missing → `403`. This stops anyone else from posting fake messages.
  2. Return `200` immediately and do the work in a background task. Meta retries when it doesn't get a quick 200, which would cause duplicate replies.
  3. Skip events that aren't incoming messages (delivery/read status updates).
  4. Skip message IDs already handled (Meta can deliver the same message twice).
  5. Text message → `ask(agent, text, thread_id=<sender's number>)` → send the reply with the Graph API.
  6. Non-text message (image, voice note, sticker…) → reply "I can only read text messages for now."
- Replies are always answers to a customer's message, so they fall inside WhatsApp's 24-hour customer-service window; no message templates are needed.

## Steps

1. Do the Meta setup above and fill in `.env`.
2. Add the settings to `.env.example` and `app/config.py`.
3. Add `GET /webhook` and `POST /webhook` to `app/main.py`.
4. Run `uvicorn app.main:app` + `ngrok http 8000`, register the webhook in Meta.
5. Test from a real phone with the checklist below.

## Done When (acceptance checklist)

- [ ] Meta's webhook verification succeeds (green tick in the dashboard).
- [ ] A WhatsApp message to the test number gets the agent's answer from the PDF.
- [ ] A follow-up from the same phone uses the earlier conversation.
- [ ] Two different phones have separate conversations.
- [ ] Greeting → short reply without search; off-topic → polite refusal.
- [ ] Image or voice note → "text only" reply, no crash.
- [ ] A POST to `/webhook` without a valid signature → `403`.
- [ ] The same message delivered twice gets only one reply.
- [ ] `POST /chat` from Phase 2 still works.

## Notes

- **Temporary token** expires after ~24 h. For longer demos create a System User token in Meta Business settings.
- **ngrok URL** changes on every restart (free plan), so the callback URL in Meta must be updated each time.
- **Memory** is still in RAM: restarting the server forgets every customer's chat. Persistent memory becomes important here (Open Decisions in PROJECT-CONTEXT.md).
- **Privacy:** phone numbers are personal data. Don't log full numbers or message text beyond what's needed for debugging.
- Message IDs for de-duplication are kept in memory (lost on restart), which is fine for a demo.

## Not in Phase 3

Our own business number (we use Meta's test number), message templates / outbound marketing, media understanding (images, voice), human handoff, persistent memory, deployment (Phase 4).
