"""LangGraph agent: the model decides when to search the company's PDFs (a tool), then answers only from the results."""
import json
import sys

from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import CHROMA_SUBDIR, COMPANY_FILE, LLM_MODEL, STORE_DIR, embeddings

TOP_K = 5          # similarity search returns this many candidates
SEND_TOP = 3       # the best this many go back to the model...
NEIGHBOURS = 1     # ...each with this many chunks before/after it, so a list split across chunks stays whole
MIN_SCORE = 0.4    # drop chunks less relevant than this (0-1); off-topic questions score ~0.35

SYSTEM_PROMPT = """You are the customer assistant for {company}, chatting with customers on a messaging app.

Rules:
- For any question about {company} (services, team, history, contact, prices, policies...), call the search_company_info tool first and answer ONLY from what it returns. Do not use outside knowledge.
- For greetings, thanks and small talk, reply briefly without searching.
- If the question is not about {company}, politely say you can only help with questions about {company}. Don't search for it.
- If the search results don't contain the answer, say you don't have that information and suggest contacting {company} directly. Never guess or invent prices, policies, dates, names or contact details.
- Keep replies short, friendly and in plain text (no markdown tables or headings).
- Reply in the same language the customer writes in."""


def load_agent():
    """Returns (compiled graph, company name). Exits with a hint if nothing has been ingested yet."""
    company_file = STORE_DIR / COMPANY_FILE
    if not company_file.exists():
        sys.exit('No company loaded. Run: python -m app.ingest --company "Name" file.pdf')
    company = json.loads(company_file.read_text())["company"]

    embedder = embeddings()
    store = Chroma(persist_directory=str(STORE_DIR / CHROMA_SUBDIR), embedding_function=embedder)
    to_score = store._select_relevance_score_fn()  # distance → 0..1 relevance, same scale as MIN_SCORE

    @tool
    def search_company_info(query: str) -> str:
        """Search the company's documents. Use a short, standalone query, e.g. "company founding date"."""
        print(f"  [search] {query!r}")
        vector = embedder.embed_query(query)  # 1. embed the query (Gemini, RETRIEVAL_QUERY)
        hits = store.similarity_search_by_vector_with_relevance_scores(vector, k=TOP_K)  # 2. top k nearest
        wanted = set()
        for rank, (doc, distance) in enumerate(hits, 1):  # 3. score, then keep the best SEND_TOP
            score = to_score(distance)
            keep = rank <= SEND_TOP and score >= MIN_SCORE
            print(f"  [rag] #{rank} {score:.2f} {'sent' if keep else 'skipped'}  chunk {doc.metadata['chunk']}: {doc.page_content[:50]!r}")
            if keep:
                i = doc.metadata["chunk"]
                wanted.update(range(i - NEIGHBOURS, i + NEIGHBOURS + 1))
        if not wanted:
            return "No relevant company information found."
        # 4. fetch hits + neighbours and send them in reading order
        got = store.get(where={"chunk": {"$in": sorted(wanted)}})
        chunks = sorted(zip(got["metadatas"], got["documents"]), key=lambda c: c[0]["chunk"])
        print(f"  [rag] sending chunks {[m['chunk'] for m, _ in chunks]}")
        return "\n\n---\n\n".join(text for _, text in chunks)

    llm = init_chat_model(LLM_MODEL).bind_tools([search_company_info])
    system = SystemMessage(SYSTEM_PROMPT.format(company=company))

    def agent(state: MessagesState):
        # ponytail: full history sent every turn; trim to last N messages if chats get long.
        return {"messages": [llm.invoke([system, *state["messages"]])]}

    graph = StateGraph(MessagesState)
    graph.add_node(agent)
    graph.add_node("tools", ToolNode([search_company_info]))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # tool call → "tools", plain reply → END
    graph.add_edge("tools", "agent")
    # ponytail: in-memory checkpointer, memory is lost on restart; swap for SqliteSaver/PostgresSaver before production.
    return graph.compile(checkpointer=InMemorySaver()), company


def ask(agent, question: str, thread_id: str) -> str:
    result = agent.invoke({"messages": [HumanMessage(question)]}, {"configurable": {"thread_id": thread_id}})
    return result["messages"][-1].text
