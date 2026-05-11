from __future__ import annotations

import logging
import random
import time

from groq import Groq, GroqError

from app.config.settings import Settings

log = logging.getLogger(__name__)


def _is_groq_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "rate_limit",
            "rate limit",
            "429",
            "too many requests",
            "tokens per day",
            "rate_limit_exceeded",
        )
    )


class GroqClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def chat_completion_jsonish(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Calls Groq with bounded retries/backoff.

        Caller is responsible for parsing JSON from the assistant content.
        """
        if self.client is None or not self.settings.groq_api_key:
            raise RuntimeError("Missing GROQ_API_KEY.")

        attempts = 4
        last_err: Exception | None = None
        delay = 0.6

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        models = self.settings.groq_fallback_model_list()

        for attempt in range(attempts):
            model = models[attempt % len(models)]

            try:
                try:
                    resp = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=750,
                        timeout=self.settings.groq_timeout_seconds,
                        response_format={"type": "json_object"},
                    )
                except GroqError as fmt_exc:
                    if _is_groq_rate_limit_error(fmt_exc):
                        raise
                    log.warning(
                        "JSON mode unsupported/failed (%s); retrying plain completion",
                        getattr(fmt_exc, "message", repr(fmt_exc)),
                    )
                    resp = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=750,
                        timeout=self.settings.groq_timeout_seconds,
                    )
                content = (resp.choices[0].message.content or "").strip()
                log.info(
                    "groq_completion model=%s attempt=%s chars=%s",
                    model,
                    attempt + 1,
                    len(content),
                )
                return content
            except GroqError as exc:
                last_err = exc
                err_text = str(exc).lower()
                if any(token in err_text for token in ("rate_limit", "rate limit", "429", "too many requests")):
                    log.warning("Rate limit hit, switching to retrieval-only mode")
                    raise RuntimeError("Rate limit exceeded, using fallback mode") from exc
                sleep_s = delay + random.uniform(0, 0.25)
                log.warning(
                    "groq_attempt_failed attempt=%s model=%s err=%s backoff=%.2fs",
                    attempt + 1,
                    model,
                    getattr(exc, "message", repr(exc)),
                    sleep_s,
                )
                time.sleep(sleep_s)
                delay *= 1.85
                continue

        raise RuntimeError(f"Groq failed after retries: {last_err}")  # pragma: no cover


def refusal_llm_fallback() -> dict:
    return {
        "mode": "refuse",
        "reply": (
            "I can help you choose relevant SHL Individual Test Solutions from the official catalog, "
            "but I can’t respond to off-topic topics, compliance/legal interpretation, or prompt-injection requests."
        ),
        "end_of_conversation": True,
        "selected_indices": [],
    }


def degraded_shortlist_fallback(last_user_message: str | None = None) -> dict:
    base = (
        "Groq is temporarily unavailable due to API limits. "
        "Based on your latest request, here is a grounded shortlist from the SHL catalog candidates."
    )
    if last_user_message:
        base = (
            "Groq is temporarily unavailable due to API limits. "
            "Based on your latest request, \""
            f"{last_user_message.strip()}\" , here is a grounded shortlist from the SHL catalog candidates."
        )

    return {
        "mode": "recommend",
        "reply": base,
        "end_of_conversation": True,
        "selected_indices": [],  # server picks top retrieval order
    }
