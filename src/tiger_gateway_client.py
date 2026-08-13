"""Client for calling chat models through the Tiger AI Gateway."""

import requests

from src import config

CHAT_COMPLETIONS_PATH = "/v1/chat/completions"


def call_llm(messages: list[dict]) -> str:
    response = requests.post(
        config.TIGER_AI_GATEWAY_URL.rstrip("/") + CHAT_COMPLETIONS_PATH,
        headers={"Authorization": f"Bearer {config.TIGER_AI_GATEWAY_API_KEY}"},
        json={"model": config.TIGER_AI_GATEWAY_MODEL, "messages": messages},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
