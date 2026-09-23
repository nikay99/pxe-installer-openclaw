from __future__ import annotations

import asyncio
import logging
from typing import Any
import httpx

from .config import Settings
from .db import Database
from .models import utcnow_iso
from .services import Analyst, NewsClient, PolymarketClient, WeKnoraClient, compute_edge

log = logging.getLogger("polyedge")


class EdgeScanner:
    def __init__(self, settings: Settings, db: Database):
        self.s = settings
        self.db = db
        self.lock = asyncio.Lock()
        self.last_markets: list[dict[str, Any]] = []
        self.last_news: list[dict[str, Any]] = []
        self.last_error: str | None = None

    async def scan(self) -> dict[str, Any]:
        if self.lock.locked():
            return {"status": "busy"}
        async with self.lock:
            scan_id = self.db.execute("INSERT INTO scans(started_at) VALUES(?)", (utcnow_iso(),))
            markets_seen = news_seen = signals_created = 0
            self.last_error = None
            try:
                timeout = httpx.Timeout(self.s.request_timeout_seconds)
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": "PolyEdge/0.1"}) as client:
                    poly = PolymarketClient(self.s, client)
                    news = NewsClient(self.s, client)
                    wk = WeKnoraClient(self.s, client)
                    analyst = Analyst(self.s, client, wk)
                    markets = await poly.get_markets()
                    markets_seen = len(markets)
                    self.last_markets = [{"id":m.id,"slug":m.slug,"question":m.question,"yes":m.yes_price,"no":m.no_price,"volume":m.volume,"liquidity":m.liquidity} for m in markets]
                    created_this_scan = 0
                    recent_news: list[dict[str, Any]] = []
                    for market in markets:
                        if created_this_scan >= self.s.max_trades_per_scan:
                            break
                        items = await news.for_market(market)
                        news_seen += len(items)
                        for item in items:
                            recent_news.append({"market":market.question,"title":item.title,"source":item.source,"url":item.url})
                            result = await analyst.analyze(market, item)
                            if not result:
                                continue
                            side, edge = compute_edge(result["probability_yes"], market.yes_price)
                            if result["relevance"] < self.s.min_relevance or result["confidence"] < self.s.min_confidence or edge < self.s.min_edge:
                                continue
                            try:
                                signal_id = self.db.execute(
                                    """INSERT INTO signals(created_at,market_id,market_slug,question,market_yes,estimated_yes,edge,side,relevance,confidence,headline,news_url,rationale)
                                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (utcnow_iso(),market.id,market.slug,market.question,market.yes_price,result["probability_yes"],edge,side,result["relevance"],result["confidence"],item.title,item.url,result["rationale"]),
                                )
                            except Exception:
                                continue
                            signals_created += 1
                            created_this_scan += 1
                            if self.s.paper_auto_trade:
                                await self._paper_trade(poly, market, side, signal_id)
                            if created_this_scan >= self.s.max_trades_per_scan:
                                break
                    self.last_news = recent_news[:50]
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.exception("scan failed")
            finally:
                self.db.execute("UPDATE scans SET finished_at=?, markets_seen=?, news_seen=?, signals_created=?, error=? WHERE id=?",(utcnow_iso(),markets_seen,news_seen,signals_created,self.last_error,scan_id))
            return {"status":"ok" if not self.last_error else "error","markets":markets_seen,"news":news_seen,"signals":signals_created,"error":self.last_error}

    async def _paper_trade(self, poly: PolymarketClient, market, side: str, signal_id: int) -> None:
        balance = self.paper_balance()
        amount = min(self.s.paper_max_trade_usd, max(1.0, balance * self.s.paper_risk_fraction))
        if amount > balance:
            return
        entry = await poly.best_ask(market.yes_token_id if side == "YES" else market.no_token_id, market.yes_price if side == "YES" else market.no_price)
        if not (0.001 < entry < 0.999):
            return
        shares = amount / entry
        self.db.execute("INSERT INTO trades(created_at,signal_id,market_id,market_slug,side,entry_price,amount_usd,shares) VALUES(?,?,?,?,?,?,?,?)",(utcnow_iso(),signal_id,market.id,market.slug,side,entry,amount,shares))

    def paper_balance(self) -> float:
        spent = float(self.db.scalar("SELECT COALESCE(SUM(amount_usd),0) AS v FROM trades WHERE status='OPEN'", default=0.0))
        return max(0.0, self.s.paper_start_balance - spent)

    def dashboard(self) -> dict[str, Any]:
        return {"status":{"scanner_busy":self.lock.locked(),"last_error":self.last_error,"llm_configured":bool(self.s.llm_base_url and self.s.llm_api_key),"weknora_configured":bool(self.s.weknora_url and self.s.weknora_api_key and self.s.weknora_kb_id),"db_path":str(self.s.db_path),"paper_balance":round(self.paper_balance(),2),"scan_interval_seconds":self.s.scan_interval_seconds},"markets":self.last_markets[:30],"news":self.last_news[:30],"signals":self.db.query("SELECT * FROM signals ORDER BY id DESC LIMIT 30"),"trades":self.db.query("SELECT * FROM trades ORDER BY id DESC LIMIT 30"),"scans":self.db.query("SELECT * FROM scans ORDER BY id DESC LIMIT 15")}
