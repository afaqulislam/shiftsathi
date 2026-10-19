"""LLM and embedding provider abstraction.

A single interface (`AIProvider`) is implemented by:

* ``OpenAICompatibleProvider`` - any OpenAI-compatible Chat Completions and
  Embeddings endpoint (OpenAI, Groq, Together, local vLLM, ...).
* ``GeminiProvider`` - Google Generative Language API (native REST), supporting
  ``gemini-*`` chat models and ``gemini-embedding-*`` embeddings.
* ``MockProvider`` - fully offline, deterministic provider used for tests and
  no-key local demos. It produces lexical-hash embeddings and an extractive
  answer so the full retrieval/generation pipeline can be exercised without a
  paid key.
* ``NullProvider`` - raises ``AIUnavailableError`` when the AI is disabled.

Keeping the provider behind an interface means the RAG code contains no
vendor-specific logic and the keys live only in server-side settings.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import AIUnavailableError

logger = logging.getLogger("shiftsathi.ai")


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return an embedding vector for each input text."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        """Return the assistant message content."""


class OpenAICompatibleProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        self._base_url = settings.AI_BASE_URL.rstrip("/")
        self._api_key = settings.AI_API_KEY
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise AIUnavailableError(
                "AI provider is not configured. Set AI_API_KEY on the server."
            )
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, headers=self._headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("AI provider HTTP error %s", exc.response.status_code)
            raise AIUnavailableError("AI provider rejected the request.") from exc
        except httpx.HTTPError as exc:
            logger.error("AI provider network error: %s", type(exc).__name__)
            raise AIUnavailableError("AI provider is unreachable.") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = await self._post(
            "/embeddings",
            {"model": settings.EMBEDDING_MODEL, "input": texts},
        )
        items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        vectors = [item["embedding"] for item in items]
        if any(len(v) != settings.EMBEDDING_DIM for v in vectors):
            raise AIUnavailableError(
                "Embedding dimension mismatch. Check EMBEDDING_MODEL/EMBEDDING_DIM."
            )
        return vectors

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": settings.CHAT_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = await self._post("/chat/completions", payload)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise AIUnavailableError("Malformed response from AI provider.") from exc


class GeminiProvider(AIProvider):
    name = "gemini"

    # batchEmbedContents accepts up to 100 inputs per request.
    _EMBED_BATCH = 50

    def __init__(self) -> None:
        self._base_url = settings.GEMINI_BASE_URL.rstrip("/")
        self._api_key = settings.GEMINI_API_KEY
        self._chat_model = settings.GEMINI_CHAT_MODEL
        self._embedding_model = settings.GEMINI_EMBEDDING_MODEL

    async def _post(
        self, model: str, method: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if not self._api_key:
            raise AIUnavailableError(
                "Gemini is not configured. Set GEMINI_API_KEY on the server."
            )
        url = f"{self._base_url}/models/{model}:{method}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.AI_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(
                    url, params={"key": self._api_key}, json=payload
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Gemini HTTP error %s: %s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise AIUnavailableError("Gemini rejected the request.") from exc
        except httpx.HTTPError as exc:
            logger.error("Gemini network error: %s", type(exc).__name__)
            raise AIUnavailableError("Gemini is unreachable.") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._EMBED_BATCH):
            batch = texts[start : start + self._EMBED_BATCH]
            payload = {
                "requests": [
                    {
                        "model": f"models/{self._embedding_model}",
                        "content": {"parts": [{"text": text}]},
                        "outputDimensionality": settings.EMBEDDING_DIM,
                    }
                    for text in batch
                ]
            }
            data = await self._post(
                self._embedding_model, "batchEmbedContents", payload
            )
            for item in data.get("embeddings", []):
                values = item.get("values", [])
                if len(values) != settings.EMBEDDING_DIM:
                    raise AIUnavailableError(
                        "Embedding dimension mismatch. Check "
                        "GEMINI_EMBEDDING_MODEL/EMBEDDING_DIM."
                    )
                vectors.append(values)
        if len(vectors) != len(texts):
            raise AIUnavailableError(
                "Gemini returned an unexpected embedding count."
            )
        return vectors

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            text = message.get("content", "")
            if role == "system":
                system_parts.append(text)
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": text}],
                }
            )

        generation_config: dict[str, Any] = {"temperature": temperature}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}]
            }

        data = await self._post(self._chat_model, "generateContent", payload)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError) as exc:
            raise AIUnavailableError("Malformed response from Gemini.") from exc


_TOKEN_RE = re.compile(r"[a-z0-9\u0600-\u06ff]+")

# Minimal stopword list so shared filler words ("of", "the", ...) do not create
# spurious similarity between unrelated texts in the offline mock provider.
_STOPWORDS = frozenset(
    """a an the and or but if while of to in on at for with from by as is are was
    were be been being it its this that these those i you he she we they them
    their our your my me us do does did doing have has had having not no yes so
    than too very can will just about into over under out up down then which who
    whom what when where how why all any both each few more most other such only
    own same don now""".split()
)


class MockProvider(AIProvider):
    """Deterministic offline provider.

    Embeddings are produced by hashing content tokens (stopwords removed) into a
    fixed-size vector and L2-normalising. This preserves lexical overlap, which
    is enough to smoke-test retrieval and abstention offline, but it is *not*
    semantic — use a real embedding model for production quality.
    """

    name = "mock"

    def _embed_one(self, text: str) -> list[float]:
        dim = settings.EMBEDDING_DIM
        vec = [0.0] * dim
        tokens = [
            t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS
        ]
        if not tokens:
            tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = -1.0 if (h >> 8) & 1 else 1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        # Extractive answer: quote the first evidence block. The RAG service
        # validates citations, so the mock only needs a well-formed response.
        user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        evidence_ids = re.findall(r"\[(\d+)\]", user)
        snippet = ""
        quote = re.search(r"\[1\] \((.*?)\)\n(.+)", user, re.DOTALL)
        if quote:
            snippet = quote.group(2).strip().split("\n")[0][:500]
        source_ids = [int(evidence_ids[0])] if evidence_ids else []
        answer = (
            "Yeh maloomat factory documents se mili hai. "
            if snippet
            else "Documents mein is sawaal ka jawab nahi mila."
        )
        if snippet:
            answer += f"Source ke mutabiq: {snippet}"
        return json.dumps(
            {
                "answer": answer,
                "source_ids": source_ids,
                "insufficient": not bool(snippet),
            }
        )


class NullProvider(AIProvider):
    name = "none"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise AIUnavailableError("AI features are disabled (AI_PROVIDER=none).")

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        raise AIUnavailableError("AI features are disabled (AI_PROVIDER=none).")


_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is None:
        provider = settings.AI_PROVIDER
        if provider == "openai":
            _provider = OpenAICompatibleProvider()
        elif provider == "gemini":
            _provider = GeminiProvider()
        elif provider == "mock":
            _provider = MockProvider()
        else:
            _provider = NullProvider()
    return _provider


def reset_ai_provider() -> None:
    """Test helper: drop the cached provider after settings change."""
    global _provider
    _provider = None
