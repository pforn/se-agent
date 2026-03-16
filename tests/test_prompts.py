from pathlib import Path

from src.llm.prompts.system_tower import load_tower_knowledge, load_iceberg_patterns, TOWER_SYSTEM_CONTEXT
from src.llm.prompts.system_fde import FDE_ROLE_CONTEXT
from src.llm.prompts.discovery import (
    GATHER_CONTEXT_PROMPT,
    ANALYZE_STACK_PROMPT,
    IDENTIFY_USE_CASES_PROMPT,
    SCORE_QUALIFICATION_PROMPT,
    GENERATE_DISCOVERY_SUMMARY_PROMPT,
)


def test_tower_knowledge_loads():
    content = load_tower_knowledge()
    assert "Tower Flows" in content
    assert "Tower Catalog" in content
    assert "Iceberg" in content


def test_iceberg_patterns_loads():
    content = load_iceberg_patterns()
    assert "Partition Evolution" in content
    assert "Small File Problem" in content


def test_system_contexts_are_nonempty():
    assert len(TOWER_SYSTEM_CONTEXT) > 100
    assert len(FDE_ROLE_CONTEXT) > 100


def test_discovery_prompts_have_placeholders():
    assert "{email_content}" in GATHER_CONTEXT_PROMPT
    assert "{tower_knowledge}" in ANALYZE_STACK_PROMPT
    assert "{tech_env_json}" in IDENTIFY_USE_CASES_PROMPT
    assert "{customer_name}" in SCORE_QUALIFICATION_PROMPT
    assert "{qualification_json}" in GENERATE_DISCOVERY_SUMMARY_PROMPT


def test_prompt_files_exist():
    prompts_dir = Path(__file__).parent.parent / "prompts"
    assert (prompts_dir / "tower_product_knowledge.md").exists()
    assert (prompts_dir / "iceberg_patterns.md").exists()
