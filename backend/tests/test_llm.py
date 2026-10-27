"""The model fallback chain (app/ai/llm.py). Building clients makes no network calls."""

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.ai import llm
from app.ai.chains import Summary
from app.config import get_settings


@pytest.fixture
def keys(monkeypatch):
    settings = get_settings()

    def set_keys(**values):
        for name in ("google", "openrouter", "nvidia", "groq"):
            monkeypatch.setattr(settings, f"{name}_api_key", values.get(name, ""))

    return set_keys


def test_chain_order_with_every_key(keys):
    keys(google="g", openrouter="o", nvidia="n", groq="q")
    s = get_settings()
    models = llm._models()
    assert [type(m) for m in models] == [
        ChatGoogleGenerativeAI,
        ChatGoogleGenerativeAI,
        ChatOpenAI,
        ChatOpenAI,
        ChatGroq,
    ]
    assert str(models[2].openai_api_base) == llm.OPENROUTER_URL
    assert models[2].model_name == s.openrouter_model
    assert str(models[3].openai_api_base) == llm.NVIDIA_URL
    assert models[3].model_name == s.nvidia_model  # DeepSeek, hosted free by NVIDIA


def test_providers_without_a_key_are_skipped(keys):
    keys(google="g", groq="q")
    assert [type(m) for m in llm._models()] == [
        ChatGoogleGenerativeAI,
        ChatGoogleGenerativeAI,
        ChatGroq,
    ]
    keys()
    with pytest.raises(RuntimeError, match="No AI provider"):
        llm._models()


async def test_an_unparsed_answer_moves_on_to_the_next_model():
    def answer(parsed):
        return RunnableLambda(
            lambda _: {"raw": AIMessage(content=""), "parsed": parsed, "parsing_error": "bad json"}
        ) | RunnableLambda(llm._require_parsed)

    good = Summary(summary="Fine.", key_points=[])
    chain = answer(None).with_fallbacks([answer(good)])
    assert (await chain.ainvoke("page"))["parsed"] == good
