from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import json


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return [value]
    return [value]


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class Market:
    id: str
    question: str
    slug: str
    description: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    end_date: str | None
    yes_token_id: str | None
    no_token_id: str | None
    raw: dict[str, Any]

    @classmethod
    def from_gamma(cls, data: dict[str, Any]) -> "Market":
        outcomes = [str(x).lower() for x in as_list(data.get("outcomes"))]
        prices = [as_float(x) for x in as_list(data.get("outcomePrices"))]
        tokens = [str(x) for x in as_list(data.get("clobTokenIds"))]

        yes_idx = outcomes.index("yes") if "yes" in outcomes else 0
        no_idx = outcomes.index("no") if "no" in outcomes else (1 if len(outcomes) > 1 else 0)
        yes_price = prices[yes_idx] if yes_idx < len(prices) else as_float(data.get("lastTradePrice"), 0.5)
        no_price = prices[no_idx] if no_idx < len(prices) else max(0.0, min(1.0, 1.0 - yes_price))

        return cls(
            id=str(data.get("id") or data.get("conditionId") or data.get("slug") or "unknown"),
            question=str(data.get("question") or data.get("title") or "Unknown market"),
            slug=str(data.get("slug") or ""),
            description=str(data.get("description") or data.get("rules") or ""),
            yes_price=max(0.0, min(1.0, yes_price)),
            no_price=max(0.0, min(1.0, no_price)),
            volume=as_float(data.get("volume") or data.get("volumeNum")),
            liquidity=as_float(data.get("liquidity") or data.get("liquidityNum")),
            end_date=data.get("endDate") or data.get("end_date_iso"),
            yes_token_id=tokens[yes_idx] if yes_idx < len(tokens) else None,
            no_token_id=tokens[no_idx] if no_idx < len(tokens) else None,
            raw=data,
        )


@dataclass(slots=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: str | None
    summary: str = ""
