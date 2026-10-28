from settle.store import Store


def make_store(tmp_path):
    return Store(tmp_path / "test.db")


def test_saved_order_is_found_by_transaction_id(tmp_path):
    store = make_store(tmp_path)
    store.save_order({"transaction_id": "tx1", "customer_name": "Ana", "amount": "49.00",
                      "items": ["Desk lamp"], "prior_orders": 3})
    order = store.get_order("tx1")
    assert order["customer_name"] == "Ana"
    assert order["items"] == ["Desk lamp"]
    assert order["prior_orders"] == 3


def test_unknown_transaction_returns_none(tmp_path):
    assert make_store(tmp_path).get_order("nope") is None


def test_analysis_round_trips(tmp_path):
    store = make_store(tmp_path)
    store.save_analysis("d1", {"verdict": "fight", "evidence_text": "Delivered."})
    assert store.get_analysis("d1")["verdict"] == "fight"
    assert store.get_analysis("missing") is None


def test_orders_by_email_lists_only_that_customer(tmp_path):
    store = make_store(tmp_path)
    store.save_order({"transaction_id": "a", "email": "x@e.com", "amount": "10.00"})
    store.save_order({"transaction_id": "b", "email": "X@e.com", "amount": "20.00"})
    store.save_order({"transaction_id": "c", "email": "y@e.com", "amount": "30.00"})
    assert sorted(o["transaction_id"] for o in store.orders_by_email("x@e.com")) == ["a", "b"]
