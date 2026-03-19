SUMMARIZE_MEETING_PROMPT = """\
Create a structured summary from the following meeting notes/transcript for {customer_name}.

<meeting_notes>
{meeting_notes}
</meeting_notes>

## Existing Context
{existing_context}

Produce a JSON object with:
- attendees: list of objects with "name" and "role"
- date: ISO date string if mentioned, else null
- key_topics: list of short topic strings discussed
- decisions: list of decisions made during the meeting
- next_steps: list of agreed next steps
- sentiment_summary: brief text summarizing overall customer sentiment
- raw_summary: 2-4 paragraph Markdown summary of the meeting

Return valid JSON only. No markdown formatting."""

EXTRACT_ACTION_ITEMS_PROMPT = """\
Extract concrete action items from this meeting summary for {customer_name}.

<meeting_summary>
{meeting_summary}
</meeting_summary>

## Existing Action Items
{existing_action_items}

For each NEW action item (not already in existing items), provide:
- description: what needs to be done
- owner: who is responsible — one of "fde", "customer", or "tower_eng"
- due_date: ISO date string if mentioned or inferable, else null
- status: "open" (all new items start as open)
- created_at: "{created_at}"

Guidelines:
- "I'll" / "we'll" from the FDE → owner = "fde"
- Customer commits to sharing/doing something → owner = "customer"
- Items requiring Tower engineering input → owner = "tower_eng"
- Be specific — "Send reference architecture to Jordan" not "Send docs"

Return a JSON array of action item objects. Skip items that duplicate existing ones."""

EXTRACT_PRODUCT_FEEDBACK_PROMPT = """\
Identify product feedback, feature requests, and capability gaps from this meeting with {customer_name}.

<meeting_summary>
{meeting_summary}
</meeting_summary>

<action_items>
{action_items_json}
</action_items>

For each piece of product feedback, provide:
- feature_area: Tower product area (e.g. "dbt integration", "catalog", "security", "performance", "scheduling", "iceberg support")
- description: what the customer needs or is concerned about
- customer: "{customer_name}"
- severity: "blocker" (deal-breaking), "important" (significant concern), or "nice_to_have"
- created_at: "{created_at}"
- ticket_url: null (to be filled when an internal ticket is created)

Focus on:
- Explicit feature requests or capability questions
- Compatibility concerns ("can Tower handle X?")
- Gaps identified vs competitors
- Performance/scale worries

Return a JSON array. Return an empty array [] if no product feedback is found."""

UPDATE_HEALTH_SCORE_PROMPT = """\
Recompute the engagement health score for {customer_name} based on all available signals.

## Current Qualification
{qualification_json}

## Stakeholders
{stakeholders_json}

## Use Cases
{use_cases_json}

## Recent Action Items
{action_items_json}

## Meeting History Count: {meeting_count}

## Current Health Score: {current_health_score}

Score 0-100 based on:
- Has champion? (+20)
- Has economic buyer identified? (+15)
- Clear pain points? (+15)
- Timeline/urgency? (+15)
- Tower fit is strong for primary use case? (+15)
- Technical environment is compatible? (+10)
- Multiple stakeholders engaged? (+10)

Also consider engagement momentum:
- Action items being completed → positive signal
- Multiple meetings → positive signal
- Blocked items or stale actions → negative signal

Return a JSON object with:
- health_score: integer 0-100
- score_breakdown: object mapping each factor to its points contribution
- change_reason: brief explanation if score changed from current

Return valid JSON only."""

DRAFT_FOLLOWUP_EMAIL_PROMPT = """\
Draft a professional follow-up email after a meeting with {customer_name}.

## Meeting Summary
{meeting_summary}

## Action Items
{action_items_json}

## Product Feedback Noted
{product_feedback_json}

## Customer Stakeholders
{stakeholders_json}

Compose a follow-up email that:
1. Thanks attendees by name
2. Summarizes key discussion points (3-5 bullets)
3. Lists action items with owners clearly marked (FDE items as "We will...", customer items as "From your side...")
4. Mentions any product feedback that was captured ("We've noted your interest in X and will follow up")
5. Proposes concrete next steps with suggested timeline
6. Keeps a professional but warm tone appropriate for a technical partnership

Return the email as plain text (not JSON). Include a suggested subject line on the first line prefixed with "Subject: "."""
