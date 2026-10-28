"""Production wiring: real Braintree sandbox, OpenAI agent, SQLite store, and the built dashboard."""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

from .agent import Agent
from .api import create_app
from .evidence import checklist, strength
from .payments import Payments
from .store import Store

load_dotenv()
store = Store(os.getenv("SETTLE_DB", "settle.db"))
payments = Payments.from_env()
llm = OpenAI()


def get_order(transaction_id):
    order = store.get_order(transaction_id) or {"note": "No order record in the shop for this transaction"}
    return {**order, "payment": payments.get_transaction(transaction_id)}


def check_evidence(transaction_id, reason):
    items = checklist(reason, store.get_order(transaction_id) or {})
    return {"items": items, "strength": strength(items)}


def get_customer_history(email):
    return [{k: o.get(k) for k in ("transaction_id", "amount", "items", "delivered_at")}
            for o in store.orders_by_email(email)]


def make_agent():
    return Agent(llm, os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
                 {"get_order": get_order, "check_evidence": check_evidence,
                  "get_customer_history": get_customer_history})


app = create_app(store, payments, make_agent)
dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
