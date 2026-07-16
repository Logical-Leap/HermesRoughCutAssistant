from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar
from pydantic import BaseModel, Field
from .store import ProjectStore

T = TypeVar("T", bound=BaseModel)

class SemanticUnit(BaseModel):
    unit_id: str
    topic: str = "general"
    purpose: str = "support"
    summary: str
    quality: float = Field(default=0.5, ge=0, le=1)
    continuity_risk: str = "none"

class SemanticResult(BaseModel):
    units: list[SemanticUnit] = Field(default_factory=list)
    topic_order: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

@dataclass
class ModelBudget:
    max_calls: int = 4
    max_tokens: int = 12000
    max_cost_usd: float = 1.0
    max_retries: int = 2
    calls: int = 0
    tokens: int = 0
    cost_usd: float = 0.0

    def charge(self, tokens: int, cost: float = 0.0) -> None:
        if self.calls + 1 > self.max_calls or self.tokens + tokens > self.max_tokens or self.cost_usd + cost > self.max_cost_usd:
            raise RuntimeError("Editorial model budget exceeded")
        self.calls += 1; self.tokens += tokens; self.cost_usd += cost

class EditorialModel(ABC):
    @abstractmethod
    def analyze(self, units: list[dict[str, Any]], budget: ModelBudget) -> SemanticResult: ...

class DeterministicEditorialModel(EditorialModel):
    def analyze(self, units: list[dict[str, Any]], budget: ModelBudget) -> SemanticResult:
        budget.charge(sum(len(str(u).split()) for u in units))
        semantic = []
        for unit in units:
            text = unit.get("text", "").strip()
            words = text.lower().split()
            topic = next((w.strip(".,!?\"") for w in words if len(w.strip(".,!?\"")) > 5), "general")
            semantic.append(SemanticUnit(unit_id=unit["id"], topic=topic, summary=text[:240] or unit.get("title", "Visual material"), quality=min(1, 0.45 + len(words) / 80)))
        return SemanticResult(units=semantic, topic_order=list(dict.fromkeys(x.topic for x in semantic)), notes=["Deterministic fallback; semantic nuance requires review."])

class OpenAICompatibleEditorialModel(EditorialModel):
    def __init__(self, endpoint: str, model: str, api_key: str = ""):
        self.endpoint, self.model, self.api_key = endpoint.rstrip("/"), model, api_key

    def analyze(self, units: list[dict[str, Any]], budget: ModelBudget) -> SemanticResult:
        prompt = "Return JSON matching SemanticResult. Analyze conservatively; do not invent facts. Units: " + json.dumps(units)
        estimated = len(prompt.split()) * 2
        budget.charge(estimated)
        body = json.dumps({"model": self.model, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": prompt}]}).encode()
        request = urllib.request.Request(self.endpoint + "/chat/completions", body, {"Content-Type": "application/json", **({"Authorization": "Bearer " + self.api_key} if self.api_key else {})})
        error = None
        for attempt in range(budget.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = json.load(response)
                return SemanticResult.model_validate_json(data["choices"][0]["message"]["content"])
            except Exception as exc:
                error = exc
                if attempt < budget.max_retries: time.sleep(2 ** attempt)
        raise RuntimeError(f"Editorial model failed after retries: {error}")
def model_from_env() -> EditorialModel:
    endpoint = os.getenv("EDITORIAL_MODEL_BASE_URL", "") or os.getenv("HERMES_EDITORIAL_ENDPOINT", "")
    if endpoint:
        return OpenAICompatibleEditorialModel(endpoint, os.getenv("EDITORIAL_MODEL_NAME", "") or os.getenv("HERMES_EDITORIAL_MODEL", "gpt-4o-mini"), os.getenv("EDITORIAL_MODEL_API_KEY", "") or os.getenv("HERMES_EDITORIAL_API_KEY", ""))
    return DeterministicEditorialModel()


def cached_analyze(store: ProjectStore, model: EditorialModel, units: list[dict[str, Any]], budget: ModelBudget) -> SemanticResult:
    key = hashlib.sha256((model.__class__.__name__ + json.dumps(units, sort_keys=True)).encode()).hexdigest()
    cached = store.rows("model_cache", "cache_key=?", (key,))
    if cached:
        payload = cached[0]["payload"]
        return SemanticResult.model_validate(payload.get("response", payload))
    before = (budget.calls, budget.tokens, budget.cost_usd)
    result = model.analyze(units, budget)
    metadata = {
        "provider": model.__class__.__name__,
        "model": getattr(model, "model", "deterministic"),
        "prompt_version": "v2-semantic-1",
        "input_hash": key,
        "token_counts": {"estimated_input": budget.tokens - before[1]},
        "estimated_cost_usd": budget.cost_usd - before[2],
        "response": result.model_dump(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    store.upsert("model_cache", {"cache_key": key, "payload": metadata, "created_at": metadata["timestamp"]})
    return result
