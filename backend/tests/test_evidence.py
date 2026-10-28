from settle.evidence import checklist, strength

GOOD_ORDER = {
    "billing_address": "12 Oak St, Austin, TX", "shipping_address": "12 Oak St, Austin, TX",
    "billing_country": "US", "ip_country": "US", "prior_orders": 3,
    "tracking_number": "1Z999", "delivered_at": "2026-10-20", "signature": True,
}


def test_fraud_with_matching_details_is_strong():
    items = checklist("fraud", GOOD_ORDER)
    assert all(i["ok"] for i in items)
    assert strength(items) == 1.0


def test_fraud_with_mismatched_address_and_new_customer_is_weak():
    order = {**GOOD_ORDER, "shipping_address": "99 Elm Rd, Miami, FL", "ip_country": "RO", "prior_orders": 0}
    items = checklist("fraud", order)
    assert strength(items) < 0.5
    assert any(not i["ok"] and "address" in i["item"].lower() for i in items)


def test_not_received_needs_tracking_and_delivery():
    items = checklist("product_not_received", {**GOOD_ORDER, "delivered_at": None})
    assert not next(i for i in items if "deliver" in i["item"].lower())["ok"]


def test_unknown_reason_uses_general_checklist():
    assert len(checklist("something_new", GOOD_ORDER)) > 0
