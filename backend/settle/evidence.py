"""Deterministic evidence checklist per dispute reason, so the agent's verdict is grounded in facts."""


def _same(a, b):
    return bool(a) and bool(b) and a.strip().lower() == b.strip().lower()


def _checks(order):
    return {
        "address": ("Shipping address matches billing address",
                    _same(order.get("shipping_address"), order.get("billing_address"))),
        "ip": ("Buyer's IP country matches billing country",
               _same(order.get("ip_country"), order.get("billing_country"))),
        "history": ("Customer has earlier undisputed orders", (order.get("prior_orders") or 0) > 0),
        "tracking": ("Order has a tracking number", bool(order.get("tracking_number"))),
        "delivered": ("Carrier confirms delivery", bool(order.get("delivered_at"))),
        "signature": ("Delivery was signed for", bool(order.get("signature"))),
    }


REASON_CHECKS = {
    "fraud": ["address", "ip", "history", "delivered"],
    "product_not_received": ["tracking", "delivered", "signature"],
}
GENERAL = ["tracking", "delivered", "history"]


def checklist(reason, order):
    checks = _checks(order)
    return [{"item": checks[k][0], "ok": checks[k][1]} for k in REASON_CHECKS.get(reason, GENERAL)]


def strength(items):
    return sum(i["ok"] for i in items) / len(items) if items else 0.0
