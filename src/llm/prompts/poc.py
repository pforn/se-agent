DESIGN_ARCHITECTURE_PROMPT = """\
Design a Tower-based target architecture for {customer_name}'s PoC engagement.

## Tower Product Knowledge
{tower_knowledge}

## Customer's Current Technical Environment
{tech_env_json}

## Identified Use Cases
{use_cases_json}

## Discovery Stack Analysis
{stack_analysis}

## Iceberg Migration Patterns
{iceberg_patterns}

Design a target architecture that:

1. **Component Mapping** — Map each current stack component to its Tower/Iceberg equivalent. Show what stays, what migrates, and what's replaced.

2. **Data Flow** — Describe the end-to-end data flow: ingestion → storage (Iceberg) → transformation (dbt/Spark) → consumption (BI/ML). Name specific pipelines based on their use cases.

3. **Migration Path** — Step-by-step migration approach. What moves first? What can run in parallel with existing stack during transition?

4. **Tower-Specific Configuration** — Catalog setup, table format decisions, partitioning strategy, compute allocation.

5. **Integration Points** — How Tower connects with components that aren't being replaced (e.g., existing orchestrator, BI tools, ML frameworks).

6. **Risk Mitigations** — For each technical risk from discovery, state the mitigation in the target architecture.

Return a JSON object with keys: component_mapping (list of objects with current/target/action), data_flow_description, migration_steps (ordered list), tower_configuration, integration_points (list), risk_mitigations (list), architecture_summary (2-3 paragraph Markdown overview)."""

GENERATE_POC_PLAN_PROMPT = """\
Create a concrete PoC plan for {customer_name}'s Tower evaluation.

## Target Architecture
{architecture_json}

## Use Cases
{use_cases_json}

## Customer's PoC Requirements
{poc_requirements}

## Customer Stakeholders
{stakeholders_json}

## Technical Environment
{tech_env_json}

Generate a detailed PoC plan with:

1. **Scope** — Which use case(s) and pipeline(s) are in scope. Be specific about data sources, transformations, and outputs.

2. **Success Criteria** — Measurable criteria that define PoC success. Include performance benchmarks, functional requirements, and any customer-specified thresholds.

3. **Timeline** — Week-by-week breakdown with milestones. Typical PoC is 2-4 weeks.

4. **Resource Requirements** — Who's needed from the customer side and Tower side, hours/week.

5. **Data Requirements** — What datasets are needed, volume, access method, any anonymization needs.

6. **Technical Setup** — Infrastructure provisioning, access requirements, environment setup steps.

7. **Demo Checkpoints** — Intermediate demos to maintain momentum and gather feedback.

8. **Risks & Contingencies** — What could derail the PoC, and backup plans.

Return a JSON object with keys: scope (object with pipelines, data_sources, outputs), success_criteria (list), timeline (list of week objects with goals), resources (list), data_requirements (list), technical_setup (list of steps), demo_checkpoints (list), risks (list of objects with risk/mitigation), poc_summary (Markdown overview)."""

COMPETITIVE_POSITIONING_PROMPT = """\
Create a competitive positioning analysis for Tower vs {competitor} for {customer_name}'s evaluation.

## Web Research Results
{research_results}

## Existing Competitive Intelligence from KB
{kb_competitive_intel}

## Customer's Technical Environment
{tech_env_json}

## Customer's Key Evaluation Criteria
{decision_criteria_json}

## Customer's Pain Points
{pain_points_json}

Produce a competitive comparison that:

1. **Head-to-Head Comparison** — Compare Tower vs {competitor} across the customer's stated decision criteria. Be honest about where Tower is weaker.

2. **Pricing/TCO Analysis** — Compare cost models. Tower's serverless model vs {competitor}'s pricing. Use the customer's scale ({data_volume_tb}TB) for rough estimates.

3. **Migration Complexity** — Compare effort to migrate from current stack to each platform.

4. **Iceberg Support** — Compare Iceberg capabilities (table format, catalog, partition evolution, time travel, etc.).

5. **Ecosystem Fit** — Compare integration with customer's existing tools (dbt, Spark, BI tools, etc.).

6. **Customer References** — Note any similar customer stories or case studies from the research.

7. **Talking Points** — 5-7 concise talking points the FDE can use in competitive discussions.

Return a JSON object with keys: comparison_matrix (list of objects with dimension/tower/competitor/winner), tco_analysis, migration_comparison, iceberg_comparison, ecosystem_fit, references (list), talking_points (list of strings), competitive_intel_items (list of objects with competitor/claim/tower_response/source)."""

CREATE_DEMO_SCRIPT_PROMPT = """\
Create a demo walkthrough script for {customer_name}'s Tower PoC.

## Target Architecture
{architecture_json}

## PoC Plan
{poc_plan_json}

## Customer Stakeholders
{stakeholders_json}

## Use Cases
{use_cases_json}

## Technical Environment
{tech_env_json}

Create a step-by-step demo script that:

1. **Opening** — Set context: remind the audience of their pain points and what the PoC aims to prove.

2. **Demo Steps** — Ordered walkthrough of the demo. For each step:
   - What you're showing and why it matters to this customer
   - Specific commands, queries, or UI actions (use their actual table/pipeline names)
   - Expected output or result
   - Talking point connecting to their pain point or evaluation criteria

3. **Comparison Points** — Where relevant, show how Tower does something better/differently than their current stack ({current_warehouse}).

4. **Q&A Prep** — Anticipated questions from each stakeholder based on their role and sentiment, with prepared answers.

5. **Next Steps Slide** — What happens after a successful demo (timeline to production, remaining evaluation steps).

Return the demo script as structured Markdown text (not JSON). Include section headers, numbered steps, and code blocks for commands/queries. Use the customer's actual data names and pipeline names from the PoC plan."""
