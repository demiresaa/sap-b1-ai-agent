"""OpenRouter (OpenAI-uyumlu) ince wrapper'ı.

Tek giriş noktası: `call_llm_json` — JSON yanıt üretir, parse eder, hata
durumunda raise eder. OpenRouter sayesinde aynı kod ile Claude, GPT, Gemini ve
diğer modellere erişebiliriz (model adını config'ten değiştirmek yeterli).

Geriye uyum: eski `call_anthropic_json` / `call_anthropic_text` adları alias
olarak korunuyor — agent kodu değiştirmeye gerek yok.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.vault import get_openrouter_api_key

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
_client_api_key: str | None = None


def get_client() -> AsyncOpenAI:
    global _client, _client_api_key
    # Vault TTL cache'inden güncel key'i al; değişmişse client'i yenile
    api_key = get_openrouter_api_key()
    if _client is None or _client_api_key != api_key:
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": settings.openrouter_site_url,
                "X-Title": settings.openrouter_app_name,
            },
        )
        _client_api_key = api_key
    return _client


def _build_messages(
    *, system: str, user_message: str, images_b64: list[str] | None
) -> list[dict[str, Any]]:
    """OpenAI/OpenRouter `messages` formatı: system + user (text + image_url[])."""
    user_content: list[dict[str, Any]] = []
    if images_b64:
        for b64 in images_b64:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
    user_content.append({"type": "text", "text": user_message})
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def _truncate(s: str, n: int = 800) -> str:
    if len(s) <= n:
        return s
    return s[:n] + f"… (+{len(s) - n} char)"


async def call_llm_json(
    *,
    system: str,
    user_message: str,
    images_b64: list[str] | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """LLM'den JSON yanıt ister, parse edip dict döner."""
    model = model or settings.llm_model_default
    messages = _build_messages(system=system, user_message=user_message, images_b64=images_b64)

    logger.info(
        "[LLM→] model=%s images=%s user_msg=%r",
        model,
        len(images_b64) if images_b64 else 0,
        _truncate(user_message, 200),
    )
    started = time.monotonic()

    try:
        response = await get_client().chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:
        logger.error(
            "[LLM✗] model=%s elapsed=%.2fs hata: %s",
            model,
            time.monotonic() - started,
            exc,
        )
        raise

    elapsed = time.monotonic() - started
    raw_text = (response.choices[0].message.content or "").strip()
    usage = getattr(response, "usage", None)
    in_tok = getattr(usage, "prompt_tokens", None) if usage else None
    out_tok = getattr(usage, "completion_tokens", None) if usage else None

    logger.info(
        "[LLM←] model=%s elapsed=%.2fs in_tok=%s out_tok=%s resp=%r",
        model,
        elapsed,
        in_tok,
        out_tok,
        _truncate(raw_text, 800),
    )

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].lstrip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("[LLM!] JSON parse hatası: %s | raw=%s", exc, raw_text[:1500])
        raise ValueError("LLM yanıtı geçerli JSON değil") from exc


async def call_llm_text(
    *,
    system: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    model = model or settings.llm_model_fast
    logger.info("[LLM→text] model=%s msg=%r", model, _truncate(user_message, 200))
    started = time.monotonic()
    response = await get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = response.choices[0].message.content or ""
    logger.info(
        "[LLM←text] model=%s elapsed=%.2fs resp=%r",
        model,
        time.monotonic() - started,
        _truncate(text, 400),
    )
    return text


async def call_llm_with_tools(
    *,
    system: str,
    user_message: str,
    tools: list[dict[str, Any]],
    tool_handler: Any,  # Callable[[str, dict], Awaitable[Any]]
    model: str | None = None,
    max_tokens: int = 4096,
    max_tool_rounds: int = 5,
) -> dict[str, Any]:
    """Tool use döngüsü: Claude araç çağırabilir, sonuçları tekrar değerlendirir.

    tool_handler(tool_name, tool_input) → Any (JSON-serializable)
    Dönen değer, Claude'a `tool` rolüyle geri gönderilir.
    Son döngüde araç yoksa normal JSON yanıt parse edilir.
    """
    model = model or settings.llm_model_default
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]
    openai_tools = [{"type": "function", "function": t} for t in tools]

    for _ in range(max_tool_rounds):
        response = await get_client().chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            tools=openai_tools,  # type: ignore[arg-type]
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=0.0,
        )
        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            # Son yanıt — JSON parse
            raw = (msg.content or "").strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:].lstrip()
            return json.loads(raw)

        # Araç çağrıları varsa — çalıştır ve mesaj geçmişine ekle
        messages.append(msg.model_dump(exclude_none=True))  # type: ignore[arg-type]
        for tc in tool_calls:
            try:
                tool_input = json.loads(tc.function.arguments or "{}")
                result = await tool_handler(tc.function.name, tool_input)
            except Exception as exc:
                result = {"error": str(exc)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise ValueError("Tool use döngüsü max_tool_rounds sınırını aştı")


async def get_embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Metinleri OpenRouter /embeddings üzerinden vektöre çevirir.

    Sonuç listesi, girdi listesiyle aynı sırada ve boyuttadır.
    """
    if not texts:
        return []
    model = model or settings.embedding_model
    response = await get_client().embeddings.create(model=model, input=texts)
    # OpenAI SDK: response.data sıralı gelir
    return [item.embedding for item in response.data]


# Geriye uyum alias'ları
call_anthropic_json = call_llm_json
call_anthropic_text = call_llm_text
