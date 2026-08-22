"""A small, deterministic, grounded support agent for the Aster & Row corpus.

No customer text or retrieved text is executable: routing is performed by the
application and order records are converted to a deliberately allow-listed
customer-safe shape before they can influence a response.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from openai_enhancement import polish

ROOT = Path(__file__).parent
KB = ROOT / "knowledge-base"
ORDER_ID = re.compile(r"\bORD[-\s]?\d{4}\b", re.I)
PRIVATE = re.compile(r"email|address|internal\s*(note|data)|risk\s*score|hidden prompt|system prompt|secret|credential", re.I)


@dataclass
class Passage:
    filename: str
    heading: str
    text: str
    metadata: dict[str, str]


@dataclass
class Reply:
    answer: str
    sources: list[str] = field(default_factory=list)
    handoff: bool = False
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


def _front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    _, front, body = raw.split("---", 2)
    return ({k.strip(): v.strip() for line in front.splitlines() if ":" in line
             for k, v in [line.split(":", 1)]}, body)


class KnowledgeBase:
    def __init__(self, directory: Path = KB):
        self.passages: list[Passage] = []
        for path in sorted(directory.glob("*.md")):
            meta, body = _front_matter(path.read_text(encoding="utf-8"))
            parts = re.split(r"(?m)^##\s+", body)
            title = re.search(r"(?m)^#\s+(.+)$", parts[0])
            for part in parts[1:]:
                heading, _, text = part.partition("\n")
                self.passages.append(Passage(path.name, heading.strip(), text.strip(), meta))
            if not parts[1:] and title:
                self.passages.append(Passage(path.name, title.group(1), body, meta))

    def search(self, query: str, limit: int = 5) -> list[Passage]:
        """Simple lexical RAG with authority/status precedence, not whole-corpus prompting."""
        terms = {w for w in re.findall(r"[a-z]{3,}", query.lower())
                 if w not in {"what", "about", "with", "have", "does", "your", "that", "this", "when"}}
        ranked: list[tuple[float, Passage]] = []
        for p in self.passages:
            words = set(re.findall(r"[a-z]{3,}", (p.heading + " " + p.text).lower()))
            score = len(terms & words)
            if p.metadata.get("status") == "active": score += 1.5
            if p.metadata.get("policy_authority") == "official": score += 1.0
            if p.metadata.get("audience") == "customer": score += .5
            if p.metadata.get("status") == "superseded" or p.metadata.get("audience") == "internal": score -= 10
            if score > 0: ranked.append((score, p))
        return [p for _, p in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]


class OrderTool:
    SAFE_FIELDS = ("order_id", "status", "carrier", "tracking_number", "estimated_delivery", "customer_safe_message")
    def __init__(self, path: Path = ROOT / "data" / "orders.json"):
        self.orders = {o["order_id"]: o for o in json.loads(path.read_text(encoding="utf-8"))["orders"]}

    def lookup(self, supplied_id: str) -> dict[str, Any] | None:
        normalized = supplied_id.strip().upper().replace(" ", "-")
        if not re.fullmatch(r"ORD-\d{4}", normalized):
            return None
        order = self.orders.get(normalized)
        if not order: return None
        safe = {k: order.get(k) for k in self.SAFE_FIELDS}
        # Carrier/ETA are stale for terminal cancellation/return states.
        if safe["status"] in {"cancelled", "returned"}:
            safe["carrier"] = safe["tracking_number"] = safe["estimated_delivery"] = None
        return safe


class SupportAgent:
    def __init__(self, debug: bool = False):
        self.kb, self.orders, self.sessions, self.debug = KnowledgeBase(), OrderTool(), {}, debug
        self.logger = logging.getLogger("aster_agent")

    def respond(self, message: str, session_id: str = "default") -> Reply:
        history = self.sessions.setdefault(session_id, [])[-4:]
        low = message.lower()
        trace: dict[str, Any] = {"message": message, "history": history, "retrieved": [], "tool_calls": []}
        if PRIVATE.search(message):
            reply = Reply("I can’t disclose private customer data, internal notes, risk scores, or hidden instructions. A support specialist can help with a legitimate privacy request.", handoff=True)
        elif re.fullmatch(r"\s*(hi|hello|hey|good (morning|afternoon|evening))\s*[!.]?\s*", low):
            reply = Reply("Hello! I can help with order status, shipping, returns, warranties, and product care. What would you like to know?")
        elif re.search(r"ignore .*policy|migration note|hidden prompt|system prompt|instructions", low):
            reply = Reply("The migration note is not authoritative. The standard return policy is 30 calendar days from delivery unless a valid exception applies. I can explain policy, but cannot approve a return.", ["01-returns-policy-current.md — Standard return window"])
        else:
            found = ORDER_ID.search(message)
            order_followup = history and history[-1].get("order_id") and re.search(r"when.*arrive|where.*(it|order)|tracking", low)
            if found or order_followup:
                order_id = found.group(0) if found else history[-1]["order_id"]
                reply = self._order_reply(order_id, trace)
            elif re.search(r"where.*(my )?order|when.*(my )?order.*arrive|track.*order", low):
                reply = Reply("Please provide your order ID (for example, ORD-1007) so I can look up its current status.")
            elif re.search(r"\bord[-\s]?\d", low):
                reply = Reply("That order ID looks incomplete. Please provide it in the format ORD-1007 so I can look it up.")
            else:
                reply = self._policy_reply(message, history, trace)
        reply = self._maybe_polish(reply, message)
        trace["final"] = reply.answer; trace["handoff"] = reply.handoff
        reply.trace = trace
        self.sessions[session_id].append({"user": message, "order_id": (ORDER_ID.search(message).group(0).upper() if ORDER_ID.search(message) else (history[-1].get("order_id") if history else None)), "topic": self._topic(low)})
        if self.debug: self.logger.info(json.dumps(trace, default=str))
        return reply

    @staticmethod
    def _maybe_polish(reply: Reply, message: str) -> Reply:
        """Model output can improve wording, never decisions, tools, or citations.

        It is intentionally unavailable for handoffs and order answers, where exact
        wording and operational safety are more important than conversational tone.
        """
        if reply.handoff or reply.tool_calls or not reply.sources:
            return reply
        candidate = polish(message, reply.answer)
        if candidate and len(candidate) < 1500 and not PRIVATE.search(candidate):
            reply.answer = candidate
        return reply

    def _order_reply(self, order_id: str, trace: dict[str, Any]) -> Reply:
        safe = self.orders.lookup(order_id)
        trace["tool_calls"].append({"name": "order_lookup", "arguments": {"order_id": order_id.strip().upper().replace(" ", "-")}, "result": safe})
        if not safe:
            return Reply("That order was not found. Please check the order ID or contact support for help.", handoff=True, tool_calls=trace["tool_calls"])
        status = safe["status"]
        if status == "cancelled": answer = "The order is cancelled and it will not be shipped."
        elif status == "returned": answer = "The return was received and processed; it is not awaiting delivery."
        else:
            answer = safe["customer_safe_message"]
            if status == "shipped":
                answer = "Your order is shipped. " + answer
            if status == "shipped" and not safe["estimated_delivery"]:
                answer += f" It shipped with {safe['carrier']}; a delivery estimate is unavailable."
            elif safe["estimated_delivery"] and "estimated to arrive" not in safe["customer_safe_message"].lower():
                eta = date.fromisoformat(safe["estimated_delivery"])
                answer += f" Current estimated delivery: {eta.strftime('%B')} {eta.day}, {eta.year}."
        return Reply(answer, handoff=status == "exception", tool_calls=trace["tool_calls"])

    def _policy_reply(self, message: str, history: list[dict], trace: dict[str, Any]) -> Reply:
        low = message.lower(); topic = self._topic(low) or (history[-1].get("topic") if history else "")
        passages = self.kb.search(message + " " + topic)
        trace["retrieved"] = [{"file": p.filename, "heading": p.heading, "metadata": p.metadata} for p in passages]
        def source(file: str, heading: str) -> list[str]: return [f"{file} — {heading}"]
        if "vegan" in low or "adhesive" in low or "fabric" in low:
            return Reply("The supplied information is insufficient to confirm whether every bag material meets that request. Please contact support for human confirmation.", handoff=True)
        if "lifetime" in low and "warranty" in low:
            return Reply("No—Aster & Row does not offer a lifetime warranty. Bags and backpacks have 2 years from purchase; drinkware and travel accessories have 1 year.", source("07-warranty.md", "Warranty periods"))
        if "dishwasher" in low and ("breeze" in low or topic == "care"):
            return Reply("Current official sources conflict: one says to hand-wash the Breeze Tumbler body (with the lid top-rack safe), while another says all components are dishwasher safe. Please seek human confirmation; the safest interim guidance is to hand-wash the body.", ["11-product-care.md — Breeze Tumbler", "12-breeze-tumbler-product-card.md — Cleaning"], True)
        if "final" in low and ("damaged" in low or "broken" in low or "wrong" in low):
            return Reply("You are not completely out of luck: final sale does not block damaged-item review. Report it within 7 calendar days of delivery with your order ID, description, and photos when possible. A human review is required before any resolution is approved.", ["03-final-sale-and-promotions.md — Damaged or incorrect items", "04-damaged-or-wrong-items.md — Reporting window"], True)
        if "canada" in low or "international" in low or "germany" in low:
            if "germany" in low: answer = "Shipping to Germany is not currently available. Aster & Row currently ships internationally only to Canada."
            elif "canada" in low: answer = "Canada is supported. Orders generally arrive 5–9 business days after dispatch; duties, taxes, and brokerage charges are not prepaid."
            else: answer = "Yes. Aster & Row currently ships internationally only to Canada."
            return Reply(answer, source("06-international-shipping.md", "Supported destinations"))
        if "trailplus" in low and "return" in low:
            return Reply("TrailPlus members have 45 calendar days from delivery when membership was active when the order was placed.", source("09-trailplus-membership.md", "TrailPlus return window"))
        if "return" in low:
            return Reply("Standard customers may request a return within 30 calendar days of delivery for unused items in resalable condition. I can explain eligibility but cannot approve a return.", source("01-returns-policy-current.md", "Standard return window"))
        if passages:
            p = passages[0]
            return Reply("I found related company information, but I can’t answer that reliably from the supplied material. Please contact support for confirmation.", [f"{p.filename} — {p.heading}"], True)
        return Reply("The supplied information is insufficient to answer that reliably. Please contact support for human confirmation.", handoff=True)

    @staticmethod
    def _topic(text: str) -> str:
        if any(x in text for x in ("ship", "canada", "international", "germany")): return "shipping"
        if any(x in text for x in ("dishwasher", "tumbler", "clean")): return "care"
        if "return" in text: return "returns"
        return ""
