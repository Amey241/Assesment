"""A short reproducible terminal demo; run with `python demo.py`."""
from aster_agent import SupportAgent

agent = SupportAgent(debug=True)
for question in [
    "How long does a regular customer have to return an unused backpack?",
    "Where is ORD-1007 and when should it arrive?",
    "Do you ship internationally?",
    "What about Canada, and how long does it take?",
    "Can I put the entire Breeze Tumbler in the dishwasher?",
]:
    reply = agent.respond(question, "demo")
    print(f"\nYou: {question}\nAgent: {reply.answer}")
    if reply.sources: print("Sources:", "; ".join(reply.sources))
    if reply.handoff: print("Human assistance recommended.")
