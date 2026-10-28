"""HTTP API for the Settle dashboard. Money actions only run on an explicit human approve/accept."""
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .evidence import checklist, strength
from .scenarios import SCENARIOS


class Approval(BaseModel):
    evidence_text: str | None = None


class Simulation(BaseModel):
    scenario: str


def create_app(store, payments, make_agent, hourly_limit=20):
    app = FastAPI(title="Settle")
    hits_by_visitor = defaultdict(deque)

    def rate_limit(request: Request):
        """Caps AI reviews and simulations per visitor, so the public demo cannot run up the OpenAI bill."""
        # shortcut: in-memory, one uvicorn worker; move to Redis if the app runs more than one process
        now, hits = time.monotonic(), hits_by_visitor[request.client.host if request.client else "unknown"]
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= hourly_limit:
            raise HTTPException(429, f"Demo limit reached: {hourly_limit} reviews or simulations per hour. Try again later.")
        hits.append(now)

    def open_dispute(dispute_id):
        dispute = payments.get_dispute(dispute_id)
        if dispute["status"] != "open":
            raise HTTPException(409, f"Dispute is {dispute['status']}, not open")
        return dispute

    @app.get("/api/disputes")
    def list_disputes():
        rows = []
        for d in payments.list_disputes():
            order = store.get_order(d["transaction_id"]) or {}
            analysis = store.get_analysis(d["id"]) or {}
            rows.append({**d, "customer_name": order.get("customer_name"), "items": order.get("items"),
                         "verdict": analysis.get("verdict"), "confidence": analysis.get("confidence")})
        return rows

    @app.get("/api/disputes/{dispute_id}")
    def get_dispute(dispute_id: str):
        d = payments.get_dispute(dispute_id)
        order = store.get_order(d["transaction_id"])
        checks = checklist(d["reason"], order or {})
        return {**d, "order": order, "analysis": store.get_analysis(dispute_id),
                "checklist": checks, "strength": strength(checks)}

    @app.post("/api/disputes/{dispute_id}/analyze", dependencies=[Depends(rate_limit)])
    def analyze(dispute_id: str):
        analysis = make_agent().run(payments.get_dispute(dispute_id))
        store.save_analysis(dispute_id, analysis)
        return analysis

    @app.post("/api/disputes/{dispute_id}/approve")
    def approve(dispute_id: str, body: Approval):
        open_dispute(dispute_id)
        analysis = store.get_analysis(dispute_id)
        if not analysis:
            raise HTTPException(409, "Analyse the dispute before submitting evidence")
        text = body.evidence_text or analysis["evidence_text"]
        payments.submit_evidence(dispute_id, text)
        store.save_analysis(dispute_id, {**analysis, "evidence_text": text, "submitted": True})
        return {"ok": True}

    @app.post("/api/disputes/{dispute_id}/accept")
    def accept(dispute_id: str):
        open_dispute(dispute_id)
        payments.accept(dispute_id)
        return {"ok": True}

    @app.post("/api/simulate", dependencies=[Depends(rate_limit)])
    def simulate(body: Simulation):
        if body.scenario not in SCENARIOS:
            raise HTTPException(422, f"Unknown scenario {body.scenario}")
        order = SCENARIOS[body.scenario]
        transaction_id = payments.create_disputed_sale(order["amount"])
        store.save_order({**order, "transaction_id": transaction_id})
        return {"transaction_id": transaction_id}

    return app
