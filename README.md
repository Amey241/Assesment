# Aster & Row reliable support agent

A deliberately small, deterministic RAG-style support agent for the take-home assignment. It has no API key or external dependency: safety-critical routing, source precedence, and order-data allow-listing are application code, so they are testable and repeatable.

## Run

Requires Python 3.10+.

```bash
git clone <your-repository-url>
cd ai-agent-intern-test
python app.py
```

Use `python app.py --debug` to emit JSON traces (message, limited history, retrieved passage metadata, sanitized tool result, final answer, and handoff). No environment variables are required; `.env.example` documents the reserved optional provider key.

For a browser interface, run `python server.py` and open `http://localhost:8080`.

```bash
python evaluation/run_evaluation.py
```

## Design

`aster_agent.py` parses Markdown front matter, splits documents at `##` headings, and stores chunks in memory with filename, heading, status, audience, and authority metadata. A lexical retriever selects only relevant chunks and strongly penalizes internal and superseded material. The answer layer additionally applies explicit policy safety rules: active official conflicts are surfaced, internal text is never treated as instruction, and every policy/product answer cites a filename and heading.

Order lookup is a separate function. It normalizes IDs and returns an allow-listed customer-safe projection only. Cancelled and returned orders suppress stale carrier, tracking, and ETA fields. The full orders JSON never reaches response composition.

Session state is keyed by `session_id`, bounded to the most recent four turns, and retains only a topic/order reference needed for a follow-up. It does not mix sessions or retain a prompt transcript indefinitely.

| Choice | Implementation |
| --- | --- |
| Model | No model required; deterministic grounded response composer |
| Retrieval | Token-overlap lexical retrieval over heading-sized Markdown chunks |
| Embeddings | None (intentional: tiny corpus, transparent precedence) |
| Framework/storage | Python standard library; in-memory index and session state |

### Optional OpenAI enhancement

The project works fully without a model. For a more natural response to low-risk, non-tool answers, create a **new, rotated** API key and set it as `OPENAI_API_KEY` in your operating-system environment; do not add it to `.env.example`, source files, or Git. Then set `OPENAI_ENHANCE=true`. The optional `openai_enhancement.py` module calls the Responses API with only application-selected answer facts. It cannot override retrieval, order lookup, privacy filtering, citations, or human-handoff decisions; it is disabled for handoffs and order answers. The API supports developer instructions and text input through the Responses create endpoint. [OpenAI API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)

## Evaluation

The evaluator runs all 15 supplied behavior cases plus seven original regression cases. It uses deterministic checks for required/forbidden claims, sources, tool invocations/arguments, privacy, and handoff—not an LLM judge.

Final result: **22/22** cases passed.

| Category | Result |
| --- | --- |
| Retrieval | 2/2 |
| Multi-source grounding | 1/1 |
| Conversation | 4/4 |
| Groundedness / abstention | 3/3 |
| Tool use / reliability | 8/8 |
| Privacy / prompt security | 3/3 |
| Source conflict | 1/1 |

Early baseline: 18/20. The first run omitted an explicit `shipped` status for an in-transit order and the abstention assertion confused a denial with a claim. Both are covered by the final suite. Two subsequent UX regression cases cover greeting and malformed order-ID behavior.

## Bug diary

1. **Shipped status was implicit.** Reproduce with `Where is ORD-1007 and when should it arrive?`; the safe carrier message said “in transit” but did not explicitly state the authoritative status. Cause: response composer used only `customer_safe_message`. Fix: prefix a shipped status from the allow-listed status field. Regression: `valid-order-lookup`.
2. **Windows date formatting failed.** Reproduce an order with an ETA on Windows. Cause: Unix-only `%-d` in `strftime`. Fix: format month, numeric day, and year portably. Regression: every ETA lookup, especially `follow-up-order`.
3. **A denial triggered a forbidden-claim assertion.** Reproduce the vegan-materials question. Cause: a naive substring checker matched “material certification” inside “cannot confirm material certification.” Fix: phrase safe abstention without repeating the unsupported claim and keep the assertion focused on actual disclosures. Regression: `insufficient-information`.

## Limits before production

- The compact deterministic intent layer is intentionally limited; a production agent should use a constrained model with structured retrieval/tool outputs and add semantic retrieval.
- Session state is in process only. Use a TTL-backed store and authenticated sessions in deployment.
- Human handoff is a recommendation, not ticket creation. No customer-changing actions are available.
- The assignment data is mock data; production requires authorization, audit controls, and access controls around order lookup.

## Demo

Run `python app.py --debug` and record the following 2–4 minute flow for the submission GIF/video: a return-window question, `ORD-1007` lookup, international-shipping then Canada follow-up, the Breeze Tumbler conflict, and `python evaluation/run_evaluation.py`. The CLI presents answers, sources, and any human-handoff recommendation directly.

### Walkthrough video

[Watch the project walkthrough on Google Drive](https://drive.google.com/file/d/1nrFxpbPOteYw6S2OC0MJsspk9tPncNVE/view?usp=sharing)

## AI tooling disclosure

Codex was used to inspect the supplied corpus, implement the standard-library application, and generate the deterministic regression harness. One incomplete suggestion caught during development was a Unix-only `strftime('%-d')` date format; it failed on Windows and was replaced with portable numeric formatting.
