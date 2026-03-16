from typing import Literal

from langchain_openai import ChatOpenAI

from src.config import settings

MODELS = {
    "fast": "anthropic/claude-haiku-4-5-20251001",
    "strong": "anthropic/claude-sonnet-4-20250514",
}


def get_llm(tier: Literal["fast", "strong"]) -> ChatOpenAI:
    return ChatOpenAI(
        model=MODELS[tier],
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        default_headers={
            "HTTP-Referer": "https://tower-fde-agent.local",
            "X-Title": "Tower FDE Agent",
        },
    )
