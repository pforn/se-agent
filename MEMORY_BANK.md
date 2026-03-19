# Tower FDE Workflow Agent — Memory Bank

> **Source of Truth** shared across Claude Code, Cursor, and Antigravity.
> Updated after every milestone.

## Project Identity

- **Name:** Tower FDE Workflow Agent
- **Purpose:** Automate administrative work for a Forward Deployed Engineer at Tower (data platform on Apache Iceberg)
- **Scope:** Discovery/qualification, PoC/demo prep, proposal drafting, post-call follow-up
- **Status:** Milestone 6 complete — Milestone 7 next

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
| 3 | ChromaDB KB + auto-indexing + retrieval | DONE |
| 4 | Follow-up subgraph + interrupt/approval + Google Drive | DONE |
| 5 | PoC subgraph + Tavily competitive research | DONE |
| 6 | Proposal subgraph | DONE |
| 7 | Dashboard + health scoring + feedback aggregation | DONE |
| 8 | Gmail live integration, prompt tuning, Docker hardening | NOT STARTED |

## Key Patterns

- **One file per graph node.** Each exports `async def node_name(state: CustomerState) -> dict`.
- **Subgraph factories.** Each phase's `__init__.py` has `build_X_subgraph()` returning compiled subgraph.
- **`interrupt()` inside nodes** (LangGraph 0.4+), not `interrupt_before` at compile time.
- **KB grows organically.** Every approved work product auto-indexed to ChromaDB. No manual curation.
- **`TechnicalEnvironment` is structured**, not free-text. Enables architecture reasoning.
- **Model routing via `get_llm(tier)`** — "fast" (Haiku) or "strong" (Sonnet).
- **`KBStore` singleton** via `get_kb_store()`. Lazy-initialized, warmed on app startup.
- **5 ChromaDB collections:** `discovery_summaries`, `stack_analyses`, `use_cases`, `competitive_intel`, `meeting_notes`.
- **KB retrieval in `analyze_stack`** — queries similar stack analyses (filtered by `cloud_provider`) and discovery summaries, injected as `{similar_contexts}` in the prompt.
- **Auto-indexing on approval.** `generate_discovery_summary` indexes discovery summary + stack analysis + use cases on approve. `analyze_stack` auto-indexes its output (no approval needed).
- **Graceful KB degradation.** All KB calls wrapped in try/except — first customer (empty KB) and KB failures don't break the graph.
- **Follow-up subgraph flow:** `summarize_meeting` → `extract_action_items` → `extract_product_feedback` → `update_health_score` → `draft_followup_email`. Linear pipeline, 4 of 5 nodes use `interrupt()`.
- **`update_health_score` is auto (no interrupt).** Recomputes health_score from all engagement signals — intermediate computation between feedback extraction and email drafting.
- **KB indexing in follow-up.** `summarize_meeting` indexes to `meeting_notes` on approve. `extract_product_feedback` indexes to `competitive_intel` on approve.
- **`index_meeting_notes(state, summary_content)`** and **`index_product_feedback(state)`** added to `src/kb/indexer.py`.
- **Google Drive integration.** `GDriveClient` in `src/integrations/gdrive.py` wraps `google-api-python-client`. `get_gdrive_client()` singleton returns `None` when no credentials — graceful degradation like KB.
- **`draft_followup_email` uploads to GDrive on approve** if `GDriveClient` is available; sets `gdrive_url` in doc record (stays `None` otherwise).
- **Edit flow pattern.** `draft_followup_email` supports approve/edit/reject like `generate_discovery_summary` — edit triggers revision LLM call then second interrupt.
- **Followup prompts** in `src/llm/prompts/followup.py` — 5 templates matching discovery prompt style.
- **PoC subgraph flow:** `design_architecture` → `generate_poc_plan` → `competitive_positioning` → `create_demo_script`. Linear pipeline, all 4 nodes use `interrupt()` with approve/edit/reject.
- **`design_architecture` stores architecture in `meeting_summaries`** as `type: "poc_architecture"` — consumed by `generate_poc_plan` and `create_demo_script` for context chaining.
- **Tavily integration.** `TavilySearchClient` in `src/integrations/tavily_search.py` wraps `tavily-python`. `get_tavily_client()` singleton returns `None` when no API key — graceful degradation like KB and GDrive.
- **`competitive_positioning` uses Tavily + KB.** Identifies competitor from `tech_env.current_warehouse`, runs 2 Tavily queries, retrieves existing KB intel, feeds all to LLM. Produces `competitive_intel` items + positioning doc.
- **`index_competitive_intel(state)`** added to `src/kb/indexer.py`. Indexes `CompetitiveIntel` items to `competitive_intel` collection with competitor metadata.
- **`create_demo_script` uploads to GDrive on approve** if `GDriveClient` is available; same pattern as `draft_followup_email`.
- **PoC prompts** in `src/llm/prompts/poc.py` — 4 templates: architecture design, PoC plan, competitive positioning, demo script.
- **Context chaining across PoC nodes.** `design_architecture` reads stack_analysis from discovery. `generate_poc_plan` reads architecture + latest message (PoC scoping email). `competitive_positioning` reads tech_env for competitor identification. `create_demo_script` reads architecture + PoC plan from generated_docs.
- **Proposal subgraph flow:** `draft_proposal` → `add_reference_architecture` → `add_deployment_plan` → `compile_document`. Linear pipeline, all 4 nodes use `interrupt()`.
- **`draft_proposal` aggregates full engagement context.** Reads discovery_summary, competitive_positioning from generated_docs, plus MEDDIC qualification, stakeholders, tech_env, and Tower product knowledge. Produces `proposal_narrative` doc type.
- **`add_reference_architecture` generates Mermaid diagrams.** Reads poc_architecture from meeting_summaries and proposal_narrative for context. Produces current/target/migration architecture diagrams as `reference_architecture` doc type.
- **`add_deployment_plan` creates phased rollout.** Reads poc_plan, proposal_narrative, architecture. 4 phases: PoC validation → production pilot → broader rollout → optimization. Produces `deployment_plan` doc type.
- **`compile_document` is a tool node (no LLM).** Assembles proposal_narrative + reference_architecture + deployment_plan into a single document. Uploads to GDrive on approve (graceful degradation if no GDrive). Produces `compiled_proposal` doc type.
- **Proposal prompts** in `src/llm/prompts/proposal.py` — 3 templates: draft_proposal, reference_architecture, deployment_plan. `compile_document` has no prompt (tool node).
- **Context chaining across proposal nodes.** `draft_proposal` reads discovery + competitive docs. `add_reference_architecture` reads PoC architecture + proposal narrative. `add_deployment_plan` reads PoC plan + architecture + proposal narrative. `compile_document` reads all 3 proposal sections.
- **Dashboard UI (Milestone 7).** `dashboard.html` — summary cards (total customers, avg health, feedback count) + recent activity feed + customer table. `customer.html` — tabbed layout (Overview/Feedback/Audit) with Chart.js health trend chart, HTMX-loaded partials.
- **Health score persistence.** `update_health_score` node persists score to `health_score_history` table and updates `customers.health_score` via `save_health_score()`. Graceful try/except — DB failure doesn't break the graph.
- **`product_feedback` table.** Flat table in app SQLite. `save_product_feedback()` batch-inserts from graph state. `get_feedback_summary()` aggregates by severity and feature area.
- **`get_dashboard_stats()` aggregation.** Single function powering summary cards: total customers, avg health score, feedback count, recent audit entries (with JOIN).

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
│   ├── test_kb/
│   └── test_integrations/
└── data/                       # Docker volume
```

## V2 Deferred Items

- Tower API/CLI access for PoC resource creation
- Meeting transcription integration
- Slack integration
- CRM sync
- Prompt versioning
- Live Gmail integration
