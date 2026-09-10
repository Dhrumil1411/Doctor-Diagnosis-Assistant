import hashlib
import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass

import httpx

from app.core.config import Settings

logger = logging.getLogger("uvicorn.error")


class LLMError(Exception):
    pass


@dataclass
class LLMProvider:
    name: str
    api_key: str
    model: str
    base_url: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def build_chain(settings: Settings) -> list[LLMProvider]:
    chain = []
    for name in [p.strip().lower() for p in settings.llm_provider_chain.split(",") if p.strip()]:
        if name == "groq":
            chain.append(
                LLMProvider(
                    name="groq",
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                    base_url="https://api.groq.com/openai/v1",
                )
            )
        elif name == "openrouter":
            chain.append(
                LLMProvider(
                    name="openrouter",
                    api_key=settings.openrouter_api_key,
                    model=settings.openrouter_model,
                    base_url="https://openrouter.ai/api/v1",
                )
            )
        else:
            logger.warning("unknown provider '%s' in LLM_PROVIDER_CHAIN, skipping", name)
    return chain


class ReasonCache:
    def __init__(self, max_size: int = 500):
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size

    @staticmethod
    def make_key(payload: dict) -> str:
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict | None:
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def put(self, key: str, value: dict) -> None:
        self._store[key] = value
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)


def extract_json_object(text: str) -> dict | None:
    # 1. Look for ```json ... ``` blocks first
    fenced_matches = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    for match in reversed(fenced_matches):
        start = match.find("{")
        end = match.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(match[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    # 2. Look for outermost braces in full response
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


class LLMClient:
    """One OpenAI-compatible client over a provider chain with auto-fallback."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self._transport = transport

    def _call_provider(self, provider: LLMProvider, messages: list[dict]) -> str:
        body = {
            "model": provider.model,
            "messages": messages,
            "max_tokens": self.settings.llm_max_tokens,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(
            timeout=self.settings.llm_timeout_seconds, transport=self._transport
        ) as client:
            resp = client.post(
                f"{provider.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {provider.api_key}"},
                json=body,
            )
        if resp.status_code != 200:
            raise LLMError(f"{provider.name} HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"{provider.name} malformed response: {exc}") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError(f"{provider.name} empty completion")
        return content

    def chat_json(self, messages: list[dict]) -> tuple[dict, str]:
        errors: list[str] = []
        attempted_any = False
        for provider in build_chain(self.settings):
            if not provider.configured:
                errors.append(f"{provider.name}: no API key configured")
                continue
            attempted_any = True
            try:
                raw = self._call_provider(provider, messages)
                parsed = extract_json_object(raw)
                if parsed is None:
                    raise LLMError(f"{provider.name} returned unparseable JSON")
                return parsed, provider.name
            except (LLMError, httpx.HTTPError) as exc:
                logger.warning("LLM provider failed (%s), falling back", exc)
                errors.append(str(exc))
        if not attempted_any:
            raise LLMError(
                "No LLM providers configured - set GROQ_API_KEY / OPENROUTER_API_KEY in .env"
            )
        raise LLMError("All LLM providers failed: " + " | ".join(errors))
