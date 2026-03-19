DRAFT_PROPOSAL_PROMPT = """\
Draft a technical proposal for {customer_name} to adopt Tower as their data platform.

## Tower Product Knowledge
{tower_knowledge}

## Customer's Technical Environment
{tech_env_json}

## Identified Use Cases
{use_cases_json}

## Qualification (MEDDIC)
- Metrics: {metrics}
- Economic Buyer: {economic_buyer}
- Decision Criteria: {decision_criteria_json}
- Decision Process: {decision_process}
- Identified Pain: {pain_points_json}
- Champion: {champion}

## Customer Stakeholders
{stakeholders_json}

## Discovery Summary
{discovery_summary}

## Competitive Positioning
{competitive_summary}

Create a narrative proposal document with these sections:

1. **Executive Summary** — 2-3 paragraphs: the customer's challenge, Tower as the solution, expected outcomes. Written for the economic buyer.

2. **Current State & Challenges** — Detail the customer's pain points, current stack limitations, and cost trajectory. Use specific numbers from their environment ({data_volume_tb}TB, etc.).

3. **Proposed Solution** — How Tower addresses each pain point. Map to their use cases. Reference specific Tower capabilities (serverless Iceberg, native dbt/Spark/Trino support, etc.).

4. **Expected Outcomes & ROI** — Quantify benefits: cost savings, performance improvements, operational simplification. Be conservative with estimates and flag assumptions.

5. **Why Tower** — Differentiation vs their current stack and evaluated alternatives. Reference competitive positioning where relevant.

6. **Engagement Summary** — Brief recap of discovery findings, PoC results, and demonstrated capabilities.

Return the proposal as structured Markdown text (not JSON). Use clear section headers and professional tone suitable for sharing with the customer's leadership."""

ADD_REFERENCE_ARCHITECTURE_PROMPT = """\
Create a reference architecture section for {customer_name}'s Tower proposal.

## PoC Architecture Design
{architecture_json}

## Customer's Technical Environment
{tech_env_json}

## Use Cases
{use_cases_json}

## Proposal Narrative (for context)
{proposal_narrative}

Generate a reference architecture section that includes:

1. **Current State Architecture** — Describe the customer's existing data stack as it is today. Include a Mermaid diagram showing data flow through current components.

2. **Target State Architecture** — Show the Tower-based target architecture. Include a Mermaid diagram with all components (ingestion, Tower/Iceberg storage, compute engines, consumption layer).

3. **Migration Architecture** — Diagram showing the transitional state where current and target systems coexist. Highlight which components run in parallel during migration.

4. **Component Mapping Table** — For each current component, show the Tower equivalent and migration action (replace/migrate/keep/extend).

5. **Integration Points** — Detail how Tower connects with components that remain (orchestrator, BI tools, ML frameworks, etc.).

6. **Sizing & Configuration** — Recommended Tower configuration based on their data volumes and query patterns.

Return as structured Markdown with Mermaid diagram code blocks (```mermaid). Use the customer's actual component names and pipeline names."""

ADD_DEPLOYMENT_PLAN_PROMPT = """\
Create a phased deployment plan for {customer_name}'s Tower adoption.

## Target Architecture
{architecture_json}

## PoC Plan & Results
{poc_plan}

## Proposal Narrative
{proposal_narrative}

## Customer Stakeholders
{stakeholders_json}

## Technical Environment
{tech_env_json}

## Data Volume: {data_volume_tb}TB

Generate a phased deployment plan:

1. **Phase 1: PoC Validation** (already complete or in progress)
   - Scope, success criteria, timeline recap
   - Results and lessons learned (reference PoC plan)

2. **Phase 2: Production Pilot**
   - First production workload migration (typically the PoC use case)
   - Parallel running period with current stack
   - Monitoring and validation criteria
   - Timeline: typically 4-6 weeks post-PoC
   - Resource requirements (customer + Tower FDE)

3. **Phase 3: Broader Rollout**
   - Additional use case migrations in priority order
   - Training plan for customer data engineering team
   - Decommissioning plan for replaced components
   - Timeline: typically 2-4 months

4. **Phase 4: Optimization & Expansion**
   - Performance tuning for production workloads
   - Advanced features (partition evolution, time travel, cross-engine queries)
   - Ongoing support model transition from FDE to standard support

5. **Risk Mitigation** — For each phase, list key risks and contingencies.

6. **Investment Summary** — Timeline, resource commitment, and expected milestones per phase.

Return as structured Markdown with clear phase headers, timelines, and milestone tables."""
