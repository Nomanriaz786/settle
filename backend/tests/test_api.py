from fastapi.testclient import TestClient

from settle.api import create_app
from settle.store import Store


class FakePayments:
    def __init__(self):
        self.disputes = {"d1": {"id": "d1", "transaction_id": "tx1", "reason": "fraud", "status": "open",
                                "amount": "49.00", "reply_by": "2026-10-30"}}
        self.submitted, self.accepted = {}, []

    def list_disputes(self):
        return list(self.disputes.values())

    def get_dispute(self, dispute_id):
        return self.disputes[dispute_id]

    def submit_evidence(self, dispute_id, text):
        self.submitted[dispute_id] = text

    def accept(self, dispute_id):
        self.accepted.append(dispute_id)

    def create_disputed_sale(self, amount):
        return "tx_new"


class FakeAgent:
    def run(self, dispute, on_step=None):
        return {"verdict": "fight", "confidence": 0.8, "reasons": ["r"], "evidence_text": "AI draft", "steps": []}


def setup(tmp_path):
    store, payments = Store(tmp_path / "t.db"), FakePayments()
    store.save_order({"transaction_id": "tx1", "customer_name": "Ana Lopez", "amount": "49.00"})
    return TestClient(create_app(store, payments, lambda: FakeAgent())), store, payments


def test_list_includes_customer_and_verdict_after_analysis(tmp_path):
    client, _, _ = setup(tmp_path)
    assert client.get("/api/disputes").json()[0]["verdict"] is None
    client.post("/api/disputes/d1/analyze")
    row = client.get("/api/disputes").json()[0]
    assert row["customer_name"] == "Ana Lopez"
    assert row["verdict"] == "fight"


def test_approve_without_analysis_is_refused(tmp_path):
    client, _, payments = setup(tmp_path)
    assert client.post("/api/disputes/d1/approve", json={}).status_code == 409
    assert payments.submitted == {}


def test_approve_submits_the_human_edited_text(tmp_path):
    client, _, payments = setup(tmp_path)
    client.post("/api/disputes/d1/analyze")
    assert client.post("/api/disputes/d1/approve", json={"evidence_text": "Edited by merchant"}).status_code == 200
    assert payments.submitted["d1"] == "Edited by merchant"


def test_approve_falls_back_to_ai_draft(tmp_path):
    client, _, payments = setup(tmp_path)
    client.post("/api/disputes/d1/analyze")
    client.post("/api/disputes/d1/approve", json={})
    assert payments.submitted["d1"] == "AI draft"


def test_closed_dispute_cannot_be_approved_or_accepted(tmp_path):
    client, _, payments = setup(tmp_path)
    client.post("/api/disputes/d1/analyze")
    payments.disputes["d1"]["status"] = "won"
    assert client.post("/api/disputes/d1/approve", json={}).status_code == 409
    assert client.post("/api/disputes/d1/accept").status_code == 409
    assert payments.submitted == {} and payments.accepted == []


def test_accept_calls_braintree(tmp_path):
    client, _, payments = setup(tmp_path)
    assert client.post("/api/disputes/d1/accept").status_code == 200
    assert payments.accepted == ["d1"]


def test_simulate_creates_order_linked_to_new_transaction(tmp_path):
    client, store, _ = setup(tmp_path)
    r = client.post("/api/simulate", json={"scenario": "friendly_fraud"})
    assert r.status_code == 200
    assert store.get_order("tx_new")["transaction_id"] == "tx_new"


def test_simulate_rejects_unknown_scenario(tmp_path):
    client, _, _ = setup(tmp_path)
    assert client.post("/api/simulate", json={"scenario": "nope"}).status_code == 422
