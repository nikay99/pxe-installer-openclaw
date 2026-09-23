from pathlib import Path
from app.db import Database
from app.models import Market
from app.services import compute_edge, lexical_relevance

def test_parse_gamma_strings():
    m=Market.from_gamma({"id":"1","question":"Will Example happen?","slug":"example","outcomes":'["Yes","No"]',"outcomePrices":'["0.42","0.58"]',"clobTokenIds":'["yes-token","no-token"]',"volume":"1000"})
    assert m.yes_price==0.42 and m.no_price==0.58 and m.yes_token_id=="yes-token"

def test_edge_both_sides():
    side,edge=compute_edge(0.70,0.50); assert side=="YES" and round(edge,6)==0.20
    side,edge=compute_edge(0.30,0.50); assert side=="NO" and round(edge,6)==0.20

def test_relevance():
    assert lexical_relevance("Will Apple release an iPhone in September?","Apple September iPhone launch expected")>0.2

def test_db(tmp_path:Path):
    db=Database(tmp_path/"x.sqlite3"); db.execute("INSERT INTO scans(started_at) VALUES(?)",("now",)); assert db.scalar("SELECT COUNT(*) AS c FROM scans")==1
