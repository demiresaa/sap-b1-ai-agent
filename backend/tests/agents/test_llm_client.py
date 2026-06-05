"""LLM client — OpenRouter wrapper sanity (HTTP mock)."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.agents.llm_client import call_llm_json, call_llm_text, get_client

BASE_URL = "https://openrouter.ai/api/v1"


@pytest.fixture(autouse=True)
def reset_client():
    """Her test başında singleton client'ı sıfırla — header isteklerini yeniden okuyalım."""
    import app.agents.llm_client as mod

    mod._client = None
    yield
    mod._client = None


@respx.mock
@pytest.mark.asyncio
async def test_get_client_points_to_openrouter() -> None:
    client = get_client()
    assert str(client.base_url).startswith(BASE_URL)


@respx.mock
@pytest.mark.asyncio
async def test_call_llm_json_parses_response() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "anthropic/claude-sonnet-4.5",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": '{"kind":"sales_order","lines":[]}'},
                    }
                ],
            },
        )
    )
    result = await call_llm_json(system="sys", user_message="hi")
    assert result == {"kind": "sales_order", "lines": []}


@respx.mock
@pytest.mark.asyncio
async def test_call_llm_json_strips_markdown_fence() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": '```json\n{"a":1}\n```'},
                    }
                ],
            },
        )
    )
    result = await call_llm_json(system="s", user_message="u")
    assert result == {"a": 1}


@respx.mock
@pytest.mark.asyncio
async def test_call_llm_json_invalid_json_raises_value_error() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "not-json"},
                    }
                ],
            },
        )
    )
    with pytest.raises(ValueError):
        await call_llm_json(system="s", user_message="u")


@respx.mock
@pytest.mark.asyncio
async def test_call_llm_json_sends_image_as_data_url() -> None:
    """Vision çağrısında base64 image data URL formatında gönderilmeli."""
    route = respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "{}"},
                    }
                ],
            },
        )
    )
    await call_llm_json(system="s", user_message="u", images_b64=["iVBORw0KG"])
    body = route.calls.last.request.read().decode("utf-8")
    assert "data:image/png;base64,iVBORw0KG" in body
    assert "image_url" in body


@respx.mock
@pytest.mark.asyncio
async def test_call_llm_text_returns_content() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Merhaba"},
                    }
                ],
            },
        )
    )
    text = await call_llm_text(system="s", user_message="u")
    assert text == "Merhaba"
