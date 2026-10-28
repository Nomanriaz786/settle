"""Seed the demo shop: real Braintree sandbox chargebacks for a spread of Kiln & Co. orders.

Some are strong cases worth fighting (repeat buyers, signed delivery), some are weak ones to accept.
Run from backend/: python -m settle.seed
"""
import os

from dotenv import load_dotenv

from .payments import Payments
from .store import Store


def _order(name, email, amount, items, billing, shipping=None, ip_country="US", prior_orders=0,
           carrier="UPS", tracking_number=None, delivered_at=None, signature=False, messages=()):
    return {"amount": amount, "customer_name": name, "email": email, "items": items,
            "billing_address": billing, "shipping_address": shipping or billing,
            "billing_country": "US", "ip_country": ip_country, "prior_orders": prior_orders,
            "carrier": carrier, "tracking_number": tracking_number, "delivered_at": delivered_at,
            "signature": signature, "messages": list(messages)}


ORDERS = [
    _order("Emily Park", "emily.park@example.com", "86.00", ["Speckled mug set (2)", "Matching saucers"],
           "22 Birch Rd, Boulder, CO 80302", prior_orders=6, tracking_number="1Z84F7E20398815510",
           delivered_at="2026-10-12", signature=True,
           messages=["Oct 13: 'Mugs arrived safely, love them.'"]),
    _order("Marcus Reid", "mreid@example.net", "245.00", ["Hand-thrown serving bowl", "Oak stand"],
           "5 Harbor St, Boston, MA 02110", shipping="1180 Desert Rd, Las Vegas, NV 89101", ip_country="NG",
           carrier="FedEx", tracking_number="7713 2209 5521", delivered_at="2026-10-17"),
    _order("Priya Nair", "priya.nair@example.com", "58.00", ["Ceramics gift card"],
           "301 Lake Dr, Chicago, IL 60601", prior_orders=2, carrier="Email delivery",
           messages=["Oct 18: 'Sent the gift card to my sister, she loved it.'"]),
    _order("Tom Becker", "tbecker@example.com", "172.00", ["Pasta bowls (6)"],
           "64 Cedar Ln, Madison, WI 53703", prior_orders=3, tracking_number="1Z84F7E20398819043",
           delivered_at="2026-10-15", signature=True),
    _order("Alyssa Grant", "alyssa.g@example.org", "312.00", ["Large planter", "Drip tray", "Express shipping"],
           "17 Willow Way, Raleigh, NC 27601", shipping="88 Canal St, New York, NY 10013", ip_country="VN",
           carrier="USPS", tracking_number="9400 1118 9922 3456 7820 11", delivered_at="2026-10-16"),
    _order("Kenji Watanabe", "kenji.w@example.com", "64.00", ["Tea bowl"],
           "903 Pine St, San Francisco, CA 94108", prior_orders=9, carrier="USPS",
           tracking_number="9400 1118 9922 3456 7833 02", delivered_at="2026-10-11",
           messages=["Oct 12: 'Another beautiful piece, thank you.'"]),
    _order("Laura Mendes", "laura.mendes@example.com", "139.00", ["Butter dish", "Salt cellar"],
           "48 Ocean Ave, San Diego, CA 92101", prior_orders=1, tracking_number="1Z84F7E20398821906",
           delivered_at="2026-10-13"),
    _order("Chris Doyle", "c.doyle@example.net", "420.00", ["Dinner set (8)"],
           "12 Elm St, Denver, CO 80203", shipping="455 Freight Way, Miami, FL 33166", ip_country="RU",
           carrier="FedEx", tracking_number="7713 2209 6630"),
    _order("Hannah Weiss", "hweiss@example.com", "92.00", ["Vase, small", "Gift wrap"],
           "7 Spring St, Portland, ME 04101", prior_orders=4, carrier="USPS",
           tracking_number="9400 1118 9922 3456 7841 77", delivered_at="2026-10-14"),
    _order("Omar Haddad", "omar.haddad@example.com", "199.00", ["Mug of the Month (3-month plan)"],
           "250 King St, Seattle, WA 98104", prior_orders=5, carrier="USPS",
           tracking_number="9400 1118 9922 3456 7855 40", delivered_at="2026-10-08",
           messages=["Oct 20: 'Can I pause the plan for December?'"]),
    _order("Grace Liu", "grace.liu@example.com", "75.00", ["Spoon rest", "Utensil crock"],
           "36 Maple Ct, Ann Arbor, MI 48104", tracking_number="1Z84F7E20398823388",
           delivered_at="2026-10-16"),
    _order("Ben Carter", "bcarter@example.org", "268.00", ["Lamp base", "Linen shade"],
           "9 River Rd, Austin, TX 78702", shipping="3300 Commerce Blvd, Houston, TX 77002", ip_country="US",
           carrier="FedEx", tracking_number="7713 2209 7741", delivered_at="2026-10-18"),
    _order("Sofia Rossi", "sofia.rossi@example.com", "118.00", ["Olive oil cruet", "Dipping plates (4)"],
           "71 Vine St, Philadelphia, PA 19106", prior_orders=2, tracking_number="1Z84F7E20398826154",
           delivered_at="2026-10-12", signature=True,
           messages=["Oct 13: 'Perfect for the dinner party!'"]),
    _order("Derek Owens", "derek.o@example.net", "355.00", ["Stoneware dinner set (6)"],
           "140 Main St, Columbus, OH 43215", shipping="77 Port Rd, Newark, NJ 07114", ip_country="BR",
           carrier="UPS", tracking_number="1Z84F7E20398829927", delivered_at="2026-10-19"),
    _order("Nina Petrova", "nina.p@example.com", "46.00", ["Ring dish"],
           "5 Garden Pl, Brooklyn, NY 11201", prior_orders=3, carrier="USPS",
           tracking_number="9400 1118 9922 3456 7869 25", delivered_at="2026-10-10"),
    _order("Jacob Hill", "jacob.hill@example.com", "184.00", ["Casserole dish", "Trivet"],
           "820 Oak Ave, Minneapolis, MN 55403", prior_orders=1, tracking_number="1Z84F7E20398831140",
           delivered_at="2026-10-15", signature=True),
    _order("Aisha Bello", "aisha.bello@example.org", "229.00", ["Pitcher", "Tumblers (4)"],
           "63 Bay St, Charleston, SC 29401", tracking_number="1Z84F7E20398834702"),
]


def seed(store, payments):
    for order in ORDERS:
        transaction_id = payments.create_disputed_sale(order["amount"])
        store.save_order({**order, "transaction_id": transaction_id})
        print(transaction_id, order["customer_name"])


if __name__ == "__main__":
    load_dotenv()
    seed(Store(os.getenv("SETTLE_DB", "settle.db")), Payments.from_env())
