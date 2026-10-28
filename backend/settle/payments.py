"""Thin wrapper over the Braintree SDK returning plain dicts for the API and the agent."""
import os

import braintree
from braintree.test.credit_card_numbers import CreditCardNumbers

DISPUTE_CARD = CreditCardNumbers.Disputes.Chargeback
ALL_STATUSES = [v for k, v in vars(braintree.Dispute.Status).items() if not k.startswith("_")]


def _dispute(d):
    return {"id": d.id, "transaction_id": d.transaction.id, "reason": d.reason, "status": d.status,
            "amount": str(d.amount_disputed), "currency": d.currency_iso_code,
            "reply_by": str(d.reply_by_date) if d.reply_by_date else None,
            "received": str(d.received_date) if d.received_date else None}


class Payments:
    def __init__(self, gateway):
        self.g = gateway

    @classmethod
    def from_env(cls):
        return cls(braintree.BraintreeGateway(braintree.Configuration(
            braintree.Environment.Sandbox, os.environ["BRAINTREE_MERCHANT_ID"],
            os.environ["BRAINTREE_PUBLIC_KEY"], os.environ["BRAINTREE_PRIVATE_KEY"])))

    def list_disputes(self):
        result = self.g.dispute.search([braintree.DisputeSearch.status.in_list(ALL_STATUSES)])
        return [_dispute(d) for d in result.disputes.items]

    def get_dispute(self, dispute_id):
        return _dispute(self.g.dispute.find(dispute_id))

    def get_transaction(self, transaction_id):
        t = self.g.transaction.find(transaction_id)
        return {"id": t.id, "amount": str(t.amount), "status": t.status, "created_at": str(t.created_at),
                "card": f"{t.credit_card_details.card_type} ending {t.credit_card_details.last_4}",
                "avs_postal_code": t.avs_postal_code_response_code, "cvv": t.cvv_response_code}

    def submit_evidence(self, dispute_id, text):
        _check(self.g.dispute.add_text_evidence(dispute_id, text))
        _check(self.g.dispute.finalize(dispute_id))

    def accept(self, dispute_id):
        _check(self.g.dispute.accept(dispute_id))

    def create_disputed_sale(self, amount):
        result = self.g.transaction.sale({
            "amount": amount, "options": {"submit_for_settlement": True},
            "credit_card": {"number": DISPUTE_CARD, "expiration_date": "12/2030", "cvv": "123"}})
        _check(result)
        return result.transaction.id


def _check(result):
    if not result.is_success:
        raise RuntimeError(result.message)
