"""LangGraph agent: retrieve relevant chunks of the company's PDFs, then answer only from them."""
import json
import sys

from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph

from app.config import CHROMA_SUBDIR, COMPANY_FILE, LLM_MODEL, STORE_DIR, embeddings

SYSTEM_PROMPT = """You are the customer assistant for {company}, chatting with customers on a messaging app.

Rules:
- Answer ONLY using the company information below. Do not use outside knowledge.
- If the question is not about {company}, politely say you can only help with questions about {company}.
- If the information below does not contain the answer, say you don't have that information and suggest contacting {company} directly. Never guess or invent prices, policies, dates, names or contact details.
- Keep replies short, friendly and in plain text (no markdown tables or headings).
- Reply in the same language the customer writes in.

Company information:
{context}"""


class State(MessagesState):
    context: str


def load_agent():
    """Returns (compiled graph, company name). Exits with a hint if nothing has been ingested yet."""
    company_file = STORE_DIR / COMPANY_FILE
    if not company_file.exists():
        sys.exit('No company loaded. Run: python -m app.ingest --company "Name" file.pdf')
    company = json.loads(company_file.read_text())["company"]

    store = Chroma(persist_directory=str(STORE_DIR / CHROMA_SUBDIR), embedding_function=embeddings())
    retriever = store.as_retriever(search_kwargs={"k": 4})
    llm = init_chat_model(LLM_MODEL)

    def retrieve(state: State):
        # ponytail: search with the last 3 user messages so follow-ups ("how much is it?") keep their topic;
        # switch to an LLM query-rewrite step if follow-up retrieval proves weak.
        recent = [m.text for m in state["messages"] if isinstance(m, HumanMessage)][-3:]
        docs = retriever.invoke("\n".join(recent))
        return {"context": "\n\n---\n\n".join(d.page_content for d in docs)}

    def answer(state: State):
        system = SystemMessage(SYSTEM_PROMPT.format(company=company, context=state["context"]))
        # ponytail: full history sent every turn; trim to last N messages if chats get long.
        return {"messages": [llm.invoke([system, *state["messages"]])]}

    graph = StateGraph(State)
    graph.add_node(retrieve)
    graph.add_node(answer)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    # ponytail: in-memory checkpointer, memory is lost on restart; swap for SqliteSaver/PostgresSaver before production.
    return graph.compile(checkpointer=InMemorySaver()), company


def ask(agent, question: str, thread_id: str) -> str:
    result = agent.invoke({"messages": [HumanMessage(question)]}, {"configurable": {"thread_id": thread_id}})
    return result["messages"][-1].text
