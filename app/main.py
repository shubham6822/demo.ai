"""HTTP API for the agent. Usage: uvicorn app.main:app --reload  (interactive docs at /docs)"""
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent import ask, load_agent

agent, company = load_agent()
app = FastAPI(title=f"{company} assistant")


class ChatIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100, description="One per conversation (later: WhatsApp number)")
    message: str = Field(min_length=1, max_length=2000)


class ChatOut(BaseModel):
    reply: str


@app.post("/chat")
def chat(body: ChatIn) -> ChatOut:
    # ponytail: sync handler runs in FastAPI's threadpool; two messages on the same thread_id at once
    # can interleave history. Add a per-thread lock if WhatsApp users double-send.
    return ChatOut(reply=ask(agent, body.message, body.thread_id))


@app.get("/health")
def health():
    return {"status": "ok", "company": company}
