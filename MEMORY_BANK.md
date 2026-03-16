# Tower FDE Workflow Agent — Memory Bank

> **Source of Truth** shared across Claude Code, Cursor, and Antigravity.
> Updated after every milestone.

## Project Identity

- **Name:** Tower FDE Workflow Agent
- **Purpose:** Automate administrative work for a Forward Deployed Engineer at Tower (data platform on Apache Iceberg)
- **Scope:** Discovery/qualification, PoC/demo prep, proposal drafting, post-call follow-up
- **Status:** Milestone 2 complete — Milestone 3 next

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Orchestration | LangGraph 0.4+ StateGraph | `interrupt()` for HITL, subgraph composition, built-in checkpointing |
| LLM inference | OpenRouter API (`langchain-openai` with `base_url` override) | Not Anthropic direct. Multi-model routing. |
| Strong model | `anthropic/claude-sonnet-4-20250514` via OpenRouter | Generation, drafting, architecture design |
| Fast model | `anthropic/claude-haiku-4-5-20251001` via OpenRouter | Classification, routing, scoring |
| Checkpointer | `langgraph-checkpoint-sqlite` (SQLite) | Zero-ops, single user. Migrate to Postgres if needed. |
| Knowledge base | ChromaDB embedded + local `all-MiniLM-L6-v2` embeddings | No server, no API costs. 80MB model, CPU-fine. |
| Web UI | FastAPI + Jinja2 + HTMX | Reactive approval flows, no SPA. SSE for status. |
| Email (v1) | Dummy fixtures in `tests/fixtures/emails/` | No live Gmail in v1. User doesn't work at Tower yet. |
| Email (v2) | `google-api-python-client` + OAuth2, polling 60s | Label-based filtering. |
| Doc output | Google Drive/Docs API | Same OAuth2 creds. Google Docs for collaboration. |
| Web research | Tavily (~$5/mo) | Competitive positioning, company research. |
| CSS | PicoCSS or Tailwind | Minimal, no build step. |
| Python | 3.12+ | Current stable, good typing. |

## Implementation Order

| # | Milestone | Status |
|---|---|---|
| 1 | State schema + graph skeleton + SQLite + FastAPI + dummy fixtures | DONE |
| 2 | Discovery subgraph + Tower product knowledge prompt | DONE |
| 3 | ChromaDB KB + auto-indexing + retrieval | NOT STARTED |
| 4 | Follow-up subgraph + interrupt/approval + Google Drive | NOT STARTED |
| 5 | PoC subgraph + Tavily competitive research | NOT STARTED |
| 6 | Proposal subgraph | NOT STARTED |
| 7 | Dashboard + health scoring + feedback aggregation | NOT STARTED |
| 8 | Gmail live integration, prompt tuning, Docker hardening | NOT STARTED |

## Key Patterns

- **One file per graph node.** Each exports `async def node_name(state: CustomerState) -> dict`.
- **Subgraph factories.** Each phase's `__init__.py` has `build_X_subgraph()` returning compiled subgraph.
- **`interrupt()` inside nodes** (LangGraph 0.4+), not `interrupt_before` at compile time.
- **KB grows organically.** Every approved work product auto-indexed to ChromaDB. No manual curation.
- **`TechnicalEnvironment` is structured**, not free-text. Enables architecture reasoning.
- **Model routing via `get_llm(tier)`** — "fast" (Haiku) or "strong" (Sonnet).

## File Structure

```
se-agent/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── MEMORY_BANK.md              ← this file
├── .cursorrules
├── .agents/skills
├── src/
│   ├── main.py                 # FastAPI entrypoint
│   ├── config.py               # pydantic-settings
│   ├── graph/
│   │   ├── router.py           # Top-level StateGraph
│   │   ├── state.py            # CustomerState schema
│   │   ├── discovery/          # 5 node files + __init__.py
│   │   ├── poc/                # 4 node files + __init__.py
│   │   ├── proposal/           # 4 node files + __init__.py
│   │   └── followup/           # 5 node files + __init__.py
│   ├── llm/
│   │   ├── models.py           # get_llm(), OpenRouter config
│   │   └── prompts/            # System prompts per phase
│   ├── kb/
│   │   ├── store.py            # ChromaDB client + retrieve_similar()
│   │   └── indexer.py          # Post-approval KB indexing
│   ├── integrations/
│   │   ├── gmail.py            # (v2) Gmail polling
│   │   ├── gdrive.py           # Google Drive/Docs
│   │   └── tavily_search.py
│   ├── ui/
│   │   ├── routes.py
│   │   ├── templates/
│   │   └── static/
│   └── db/
│       └── app_db.py           # App SQLite
├── prompts/                    # Long-form Markdown templates
├── tests/
│   ├── fixtures/emails/        # Dummy email data
│   ├── test_graph/
│   └── test_kb/
└── data/                       # Docker volume
```

## V2 Deferred Items

- Tower API/CLI access for PoC resource creation
- Meeting transcription integration
- Slack integration
- CRM sync
- Prompt versioning
- Live Gmail integration
