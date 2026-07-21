"""
Provider-agnostic LLM client.

Every AI call site in the app goes through LLMClient.generate_text() /
generate_json() rather than talking to a provider SDK directly. Gemini
is the only provider wired up in Phase 2; OpenAI and Ollama are later
phases per the roadmap, and will be added as sibling methods behind
this same interface — call sites won't need to change.

No model name is hard-coded: GEMINI_MODEL comes from config, which
reads it from the environment. If AI isn't configured, is_available()
returns False and every call site is expected to check that (or catch
LLMError) and fall back to a clear "AI is disabled" message rather
than crashing.
"""

import json
import time

import config

# Gemini errors worth a short automatic retry: transient server-side
# overload, not something the caller did wrong. Quota/auth errors are
# deliberately excluded — retrying those just wastes the retry budget.
_RETRYABLE_STATUSES = {"UNAVAILABLE", "DEADLINE_EXCEEDED"}
_RETRY_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 2


class LLMError(Exception):
    """Raised when an LLM call fails or is unavailable."""


def _friendly_message(e: Exception) -> str:
    """
    Translate a raw google.genai error into a short, human-readable
    message instead of surfacing the full API error payload to the UI.
    Falls back to the raw exception text for anything unrecognized.
    """
    code = getattr(e, "code", None)
    status = getattr(e, "status", None)

    if status == "RESOURCE_EXHAUSTED" or code == 429:
        return (
            "Gemini's free-tier daily quota has been reached for this model. "
            "It resets on a rolling daily window — try again later, or switch "
            "to a paid plan / different GEMINI_MODEL in your environment."
        )
    if status == "UNAVAILABLE" or code == 503:
        return "Gemini is temporarily overloaded. Please try your question again in a moment."
    if status in ("PERMISSION_DENIED", "UNAUTHENTICATED") or code in (401, 403):
        return "Gemini rejected the request — check that GEMINI_API_KEY is valid and active."
    if status == "INVALID_ARGUMENT" or code == 400:
        return f"Gemini rejected the request as invalid: {getattr(e, 'message', e)}"

    return f"LLM request failed: {e}"


class LLMClient:
    def __init__(self):
        self.enabled = config.AI_ENABLED
        self._model = None
        self._genai_client = None
        self._init_error = None

        if not self.enabled:
            self._init_error = config.AI_DISABLED_REASON
            return

        try:
            from google import genai

            self._genai_client = genai.Client(api_key=config.GEMINI_API_KEY)
            self._model = config.GEMINI_MODEL  # model name is passed per-call, not bound to an object
        except Exception as e:  # noqa: BLE001 — any init failure disables AI, never crashes the app
            self.enabled = False
            self._init_error = (
                f"Could not initialize the Gemini client ({e}). "
                "Check GEMINI_API_KEY and GEMINI_MODEL."
            )

    def is_available(self) -> bool:
        return self.enabled and self._genai_client is not None and bool(self._model)

    def unavailable_reason(self) -> str:
        return self._init_error or "AI features are disabled."

    def generate_text(self, prompt: str) -> str:
        if not self.is_available():
            raise LLMError(self.unavailable_reason())

        last_error = None
        for attempt in range(_RETRY_ATTEMPTS + 1):
            try:
                response = self._genai_client.models.generate_content(model=self._model, contents=prompt)
                text = getattr(response, "text", None)
                if not text:
                    raise LLMError("The AI provider returned an empty response.")
                return text.strip()
            except LLMError:
                raise
            except Exception as e:  # noqa: BLE001
                last_error = e
                status = getattr(e, "status", None)
                is_last_attempt = attempt == _RETRY_ATTEMPTS
                if status in _RETRYABLE_STATUSES and not is_last_attempt:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise LLMError(_friendly_message(e))

        # Unreachable in practice (the loop always returns or raises above),
        # but keeps the method's control flow explicit for readers/linters.
        raise LLMError(_friendly_message(last_error) if last_error else "LLM request failed.")

    def generate_json(self, prompt: str):
        text = self.generate_text(prompt)
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMError(f"The AI provider did not return valid JSON: {e}")


_client_instance = None


def get_llm_client() -> LLMClient:
    """Return a process-wide LLMClient singleton (avoids re-initializing per call)."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance


def reset_llm_client() -> None:
    """Force re-initialization on the next get_llm_client() call. Used by tests."""
    global _client_instance
    _client_instance = None
