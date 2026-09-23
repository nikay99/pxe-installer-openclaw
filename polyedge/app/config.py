from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PolyEdge"
    scan_interval_seconds: int = 300
    max_markets: int = 12
    news_per_market: int = 8
    min_relevance: float = 0.60
    min_confidence: float = 0.60
    min_edge: float = 0.08
    paper_auto_trade: bool = True
    paper_start_balance: float = 10000.0
    paper_risk_fraction: float = 0.01
    paper_max_trade_usd: float = 100.0
    max_trades_per_scan: int = 3
    data_dir: str = "/data"

    gamma_url: str = "https://gamma-api.polymarket.com"
    clob_url: str = "https://clob.polymarket.com"
    gdelt_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    google_news_url: str = "https://news.google.com/rss/search"

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4.1-mini"

    weknora_url: str | None = None
    weknora_api_key: str | None = None
    weknora_kb_id: str | None = None

    request_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def db_path(self) -> Path:
        requested = Path(self.data_dir)
        try:
            requested.mkdir(parents=True, exist_ok=True)
            probe = requested / ".polyedge-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return requested / "polyedge.sqlite3"
        except OSError:
            fallback = Path("./data")
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback / "polyedge.sqlite3"


settings = Settings()
