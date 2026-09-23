# PolyEdge

Railway-ready Polymarket news-edge scanner with paper trading.

- FastAPI dashboard
- Polymarket Gamma + CLOB
- Google News + GDELT
- OpenAI-compatible LLM probability estimates
- Optional WeKnora retrieval
- SQLite only; no external DB/passwords
- Paper trading only by default

Railway: set root directory to /polyedge, healthcheck to /health. LLM variables are optional for boot, but required for AI signals.
