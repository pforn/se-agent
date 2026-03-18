GATHER_CONTEXT_PROMPT = """\
Analyze the following email/notes and extract structured information about the prospect's technical environment and stakeholders.

<email>
{email_content}
</email>

{existing_context}

Extract and return a JSON object with two keys:

1. "tech_env": Update the technical environment with any information found. Include:
   - current_warehouse, compute_engines, storage_layer, table_format, catalog, orchestrator
   - data_volume_tb, daily_ingestion_gb, query_engines, source_systems
   - cloud_provider (one of: aws, gcp, azure, multi)
   - governance_tools, pain_points, migration_status
   Only include fields where you have information. Use null for explicitly unknown values.

2. "stakeholders": List of people mentioned with:
   - name, role, influence (champion/evaluator/blocker/end_user), sentiment (positive/neutral/skeptical/unknown), notes

Return valid JSON only. No markdown formatting."""

ANALYZE_STACK_PROMPT = """\
You are analyzing a prospect's technical stack for Tower FDE engagement.

## Tower Product Knowledge
{tower_knowledge}

## Iceberg Migration Patterns
{iceberg_patterns}

## Similar Customer Experiences
{similar_contexts}

## Customer's Technical Environment
{tech_env_json}

## Existing Stakeholders
{stakeholders_json}

Analyze this stack and provide:

1. **Stack Assessment:** Summarize the customer's current architecture and where they are in their data platform journey.

2. **Tower Fit Analysis:** How well does Tower fit their needs? Consider:
   - Migration complexity from their current stack
   - Which Tower components map to their current tools
   - Known compatibility issues or limitations

3. **Risk Factors:** Technical risks for this engagement (e.g., unsupported features, complex migrations, scale concerns).

4. **Similar Patterns:** Based on the Iceberg patterns knowledge, what migration patterns and gotchas are relevant?

5. **Recommended Approach:** How should the FDE approach this engagement technically?

Return your analysis as a structured JSON object with keys: stack_assessment, tower_fit_analysis, risk_factors (list of strings), relevant_patterns (list of strings), recommended_approach."""

IDENTIFY_USE_CASES_PROMPT = """\
Based on the customer's technical environment and the FDE's analysis, identify concrete use cases where Tower can help.

## Customer Technical Environment
{tech_env_json}

## Pain Points
{pain_points_json}

## Stack Analysis
{stack_analysis}

## Tower Product Knowledge
{tower_knowledge}

For each use case, provide:
- name: Short descriptive name
- description: What the use case involves
- data_sources: Which source systems are involved
- target_consumers: Who/what consumes the output (BI tools, ML pipelines, APIs, etc.)
- latency_requirement: "batch daily", "< 15 min", "streaming", etc. Use null if unknown.
- current_solution: How they solve it today (null if greenfield)
- tower_fit: "strong", "moderate", "weak", or "unknown" — be honest
- notes: Any caveats, risks, or Tower limitations relevant to this use case

Return a JSON array of use case objects. Aim for 2-5 use cases. Prioritize by tower_fit strength."""

SCORE_QUALIFICATION_PROMPT = """\
Score this prospect using a MEDDIC-adapted framework for technical engagement.

## Customer: {customer_name}

## Technical Environment
{tech_env_json}

## Stakeholders
{stakeholders_json}

## Use Cases
{use_cases_json}

## Pain Points
{pain_points_json}

Evaluate and return a JSON object with:
- metrics: What quantified business impact do they care about? (cost savings, performance, time-to-insight). String or null.
- economic_buyer: Who controls the budget? Name or null.
- decision_criteria: List of technical evaluation criteria they've stated or implied.
- decision_process: How will they decide? (bake-off, PoC, committee, executive mandate). String or null.
- identified_pain: List of business-level pain points (not just technical).
- champion: Name of the internal champion, or null.
- health_score: 0-100 integer based on:
  - Has champion? (+20)
  - Has economic buyer identified? (+15)
  - Clear pain points? (+15)
  - Timeline/urgency? (+15)
  - Tower fit is strong for primary use case? (+15)
  - Technical environment is compatible? (+10)
  - Multiple stakeholders engaged? (+10)

Return valid JSON only."""

GENERATE_DISCOVERY_SUMMARY_PROMPT = """\
Generate a discovery summary document for the FDE to review before sharing with the Tower team.

## Customer: {customer_name}

## Technical Environment
{tech_env_json}

## Stakeholders
{stakeholders_json}

## Use Cases
{use_cases_json}

## MEDDIC Qualification
{qualification_json}

## Stack Analysis
{stack_analysis}

Generate a well-structured discovery summary in Markdown with these sections:

1. **Executive Summary** — 2-3 sentences: who they are, what they need, why Tower.
2. **Current Architecture** — Their stack, formatted clearly.
3. **Pain Points & Drivers** — Why they're looking at alternatives. Include business context.
4. **Identified Use Cases** — Table with name, Tower fit, notes.
5. **Stakeholder Map** — Who's involved, their role, sentiment.
6. **Qualification (MEDDIC)** — Metrics, Economic Buyer, Decision Criteria, Decision Process, Identified Pain, Champion. Health score.
7. **Recommended Next Steps** — What the FDE should do next (2-4 concrete actions).
8. **Risks & Open Questions** — What we don't know yet, what could go wrong.

Mark anything uncertain with [NEEDS REVIEW]. Be concise but thorough."""
