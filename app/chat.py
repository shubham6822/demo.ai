"""Chat with the agent in the terminal. Usage: python -m app.chat"""
from app.agent import ask, load_agent

agent, company = load_agent()
print(f"Chatting with {company}'s assistant. Type 'exit' to quit.")

while True:
    try:
        question = input("\nYou: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if question.lower() in {"exit", "quit"}:
        break
    if question:
        print(f"Bot: {ask(agent, question, thread_id='terminal')}")
