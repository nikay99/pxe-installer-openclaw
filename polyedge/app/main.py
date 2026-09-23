from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .config import settings
from .db import Database
from .scanner import EdgeScanner

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log=logging.getLogger("polyedge")
db=Database(settings.db_path)
scanner=EdgeScanner(settings,db)

async def scheduler_loop()->None:
    await asyncio.sleep(3)
    while True:
        try: await scanner.scan()
        except asyncio.CancelledError: raise
        except Exception: log.exception("scheduler scan failed")
        await asyncio.sleep(max(60,settings.scan_interval_seconds))

@asynccontextmanager
async def lifespan(app:FastAPI):
    task=asyncio.create_task(scheduler_loop(),name="polyedge-scanner")
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

app=FastAPI(title="PolyEdge",version="0.1.0",lifespan=lifespan)

@app.get("/health")
def health(): return {"ok":True,"app":settings.app_name}

@app.get("/api/dashboard")
def dashboard(): return scanner.dashboard()

@app.post("/api/scan")
async def run_scan(): return await scanner.scan()

@app.get("/",response_class=HTMLResponse)
def home():
    return HTMLResponse("""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>PolyEdge</title><style>body{font-family:system-ui;background:#0b0d10;color:#e8edf2;margin:0}.wrap{max-width:1200px;margin:auto;padding:24px}.card,section{background:#12161b;border:1px solid #252c34;border-radius:14px;padding:16px;margin:12px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.v{font-size:28px;font-weight:800}.muted{color:#9aa6b2}button{padding:10px 14px;border:0;border-radius:10px;font-weight:700}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #252c34;text-align:left}a{color:#9ecbff}.yes{color:#65d18a}.no{color:#ff7b7b}</style></head><body><div class=wrap><h1>PolyEdge</h1><p class=muted>Polymarket news-edge scanner · paper trading only</p><button id=scan>Scan now</button><div class=cards id=cards></div><section><h2>Signals</h2><div id=signals></div></section><section><h2>Paper trades</h2><div id=trades></div></section><section><h2>Top markets</h2><div id=markets></div></section><section><h2>Scan history</h2><div id=scans></div></section></div><script>
const e=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));const p=n=>(Number(n||0)*100).toFixed(1)+'%';const t=(h,r)=>'<table><thead><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+r.join('')+'</tbody></table>';
async function load(){let d=await fetch('/api/dashboard').then(r=>r.json()),s=d.status;document.getElementById('cards').innerHTML=[['Paper balance','$'+s.paper_balance],['LLM',s.llm_configured?'READY':'NOT SET'],['WeKnora',s.weknora_configured?'READY':'OPTIONAL'],['Scanner',s.scanner_busy?'RUNNING':'IDLE']].map(x=>'<div class=card><div class=muted>'+x[0]+'</div><div class=v>'+x[1]+'</div></div>').join('');document.getElementById('signals').innerHTML=t(['Market','Side','Market','Model','Edge','News'],d.signals.map(x=>'<tr><td>'+e(x.question)+'</td><td class='+(x.side==='YES'?'yes':'no')+'>'+x.side+'</td><td>'+p(x.market_yes)+'</td><td>'+p(x.estimated_yes)+'</td><td>'+p(x.edge)+'</td><td><a target=_blank href="'+e(x.news_url)+'">'+e(x.headline)+'</a></td></tr>'));document.getElementById('trades').innerHTML=t(['Side','Entry','USD','Status'],d.trades.map(x=>'<tr><td>'+x.side+'</td><td>'+p(x.entry_price)+'</td><td>$'+Number(x.amount_usd).toFixed(2)+'</td><td>'+x.status+'</td></tr>'));document.getElementById('markets').innerHTML=t(['Market','YES','Volume'],d.markets.map(x=>'<tr><td>'+e(x.question)+'</td><td>'+p(x.yes)+'</td><td>$'+Number(x.volume||0).toLocaleString()+'</td></tr>'));document.getElementById('scans').innerHTML=t(['Started','Markets','News','Signals','Error'],d.scans.map(x=>'<tr><td>'+e(x.started_at)+'</td><td>'+x.markets_seen+'</td><td>'+x.news_seen+'</td><td>'+x.signals_created+'</td><td>'+e(x.error||'')+'</td></tr>'))}
document.getElementById('scan').onclick=async()=>{await fetch('/api/scan',{method:'POST'});await load()};load();setInterval(load,10000);
</script></body></html>""")
