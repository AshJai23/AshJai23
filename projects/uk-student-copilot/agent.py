"""Bounded LangGraph workflow: privacy guard -> route -> read -> respond."""
import os
import re
from typing import TypedDict
# Questions stay local, including when a developer has tracing variables set.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from langgraph.graph import END, START, StateGraph
from sources import CARDS, NOTICE, lexical


class State(TypedDict, total=False):
    question: str
    nation: str
    blocked: bool
    topics: list
    routing: dict
    sources: list
    answer: dict


def build_agent(store, router):
    def guard(s):
        q = s["question"]
        pii = bool(re.search(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b|\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b|\b\d{9,}\b", q, re.I))
        return {"blocked": pii}
    def route(s):
        ranked, scores = lexical(s["question"])
        proposal = router.propose(s["question"]) if ranked else {"mode": "not_called", "topic": None, "reason": "No supported topic match"}
        topics = ranked[:2]
        # LLM can break lexical ties, but cannot introduce unsupported topics.
        if len(topics) == 2 and scores[topics[0]] == scores[topics[1]] and proposal.get("topic") in topics:
            topics.sort(key=lambda t: t != proposal["topic"])
        return {"topics": topics, "routing": {**proposal, "baseline_topics": ranked[:2], "selected_topics": topics}}
    def fetch(s):
        return {"sources": [store.get(t) for t in s["topics"]]}
    def respond(s):
        if s["blocked"]:
            return {"answer": {"status": "privacy_block", "message": "Remove personal identifiers and ask a general question. Nothing from this question is stored in the support log.", "cards": [], "notice": NOTICE}}
        cards = []
        for source in s["sources"]:
            topic = source["topic"]; card = CARDS[topic]
            nation_note = None
            if topic == "housing" and s["nation"] in ("Scotland", "Northern Ireland"):
                nation_note = "Use the separate " + s["nation"] + " scheme linked in the official guide; England's rules must not be applied automatically."
            if topic == "tax" and s["nation"] == "Northern Ireland":
                cards.append({"topic": topic, "title": "Northern Ireland uses domestic rates", "summary": "This Council Tax card does not cover Northern Ireland. Ask your university or council about domestic rates.", "actions": [], "source": source, "nation_note": "Council Tax guidance withheld for Northern Ireland."}); continue
            verified = source["status"] == "verified"
            cards.append({"topic": topic, "title": card["title"], "summary": card["summary"] if verified else "The source could not be verified against the reviewed checks. Open the official page and ask your university adviser; this summary is withheld.", "actions": card["actions"] if verified else [], "source": source, "nation_note": nation_note})
        status = "answered" if cards and all(c["source"]["status"] == "verified" for c in cards) else "source_problem" if cards else "out_of_scope"
        return {"answer": {"status": status, "message": "Here are the relevant official guidance cards." if cards else "I cover student work, Graduate visas, renting, Council Tax and scams. For another topic, contact your university support team.", "cards": cards, "routing": s["routing"], "notice": NOTICE,
                           "handoff": "For an individual decision, ask your university international student advice team. Quote the support reference if reporting a problem with this app."}}
    graph = StateGraph(State)
    for name, fn in (("guard", guard), ("route", route), ("fetch", fetch), ("respond", respond)): graph.add_node(name, fn)
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", lambda s: "respond" if s["blocked"] else "route")
    graph.add_edge("route", "fetch"); graph.add_edge("fetch", "respond"); graph.add_edge("respond", END)
    return graph.compile()
