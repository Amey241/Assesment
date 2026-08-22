"""Interactive CLI: python app.py [--debug]. Type /quit to exit."""
import argparse, logging
from aster_agent import SupportAgent

parser = argparse.ArgumentParser(); parser.add_argument("--debug", action="store_true")
args = parser.parse_args()
if args.debug: logging.basicConfig(level=logging.INFO, format="%(message)s")
agent = SupportAgent(debug=args.debug)
print("Aster & Row support. Type /quit to exit.")
while True:
    try: message = input("You: ").strip()
    except EOFError: break
    if message.lower() in {"/quit", "/exit"}: break
    if message: 
        result = agent.respond(message)
        print("\nAgent:", result.answer)
        if result.sources: print("Sources:", *result.sources, sep="\n- ")
        if result.handoff: print("Human assistance recommended.")
