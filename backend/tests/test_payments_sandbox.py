"""Integration test against the real Braintree sandbox. Skipped when no credentials are set."""
import os
import time

import pytest
from dotenv import load_dotenv

load_dotenv()
pytestmark = pytest.mark.skipif(not os.getenv("BRAINTREE_PRIVATE_KEY"), reason="no sandbox credentials")


def test_disputed_sale_creates_open_dispute_visible_in_list():
    from settle.payments import Payments
    payments = Payments.from_env()
    tx = payments.create_disputed_sale("12.34")
    for _ in range(10):
        found = [d for d in payments.list_disputes() if d["transaction_id"] == tx]
        if found:
            break
        time.sleep(2)
    assert found, "sandbox did not raise a dispute"
    d = payments.get_dispute(found[0]["id"])
    assert d["status"] == "open"
    assert d["amount"] == "12.34"
    assert d["reason"] == "fraud"
    payments.accept(d["id"])  # close it so test disputes do not clutter the demo
