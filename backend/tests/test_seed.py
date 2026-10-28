from settle import seed
from settle.scenarios import SCENARIOS
from settle.store import Store


class FakePayments:
    def __init__(self):
        self.sales = []

    def create_disputed_sale(self, amount):
        self.sales.append(amount)
        return f"tx{len(self.sales)}"


def test_seed_orders_have_the_same_fields_as_the_demo_scenarios():
    fields = set(next(iter(SCENARIOS.values())))
    for order in seed.ORDERS:
        assert set(order) == fields, order["customer_name"]


def test_seed_saves_one_order_per_sandbox_sale(tmp_path):
    store, payments = Store(str(tmp_path / "s.db")), FakePayments()
    seed.seed(store, payments)
    assert payments.sales == [o["amount"] for o in seed.ORDERS]
    assert store.get_order("tx1")["customer_name"] == seed.ORDERS[0]["customer_name"]
