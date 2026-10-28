"""Demo orders for Kiln & Co., a small ceramics shop, each paired with a sandbox chargeback."""

SCENARIOS = {
    "friendly_fraud": {
        "amount": "129.00", "customer_name": "Sarah Chen", "email": "sarah.chen@example.com",
        "items": ["Stoneware dinner set (4)"], "billing_address": "418 Maple Ave, Portland, OR 97205",
        "shipping_address": "418 Maple Ave, Portland, OR 97205", "billing_country": "US", "ip_country": "US",
        "prior_orders": 4, "carrier": "UPS", "tracking_number": "1Z84F7E20398812274",
        "delivered_at": "2026-10-14", "signature": True,
        "messages": ["Oct 15: 'The set arrived, thank you! The glaze is gorgeous.'"],
    },
    "stolen_card": {
        "amount": "389.00", "customer_name": "J. Mills", "email": "jm4471@example.net",
        "items": ["Large floor vase", "Gift wrap", "Express shipping"],
        "billing_address": "77 Pine St, Seattle, WA 98101", "shipping_address": "2290 NW 7th Ave, Miami, FL 33127",
        "billing_country": "US", "ip_country": "RO", "prior_orders": 0, "carrier": "FedEx",
        "tracking_number": "7713 2209 4410", "delivered_at": "2026-10-16", "signature": False, "messages": [],
    },
    "forgotten_subscription": {
        "amount": "49.00", "customer_name": "Daniel Okafor", "email": "d.okafor@example.com",
        "items": ["Mug of the Month (October)"], "billing_address": "9 Elm Ct, Austin, TX 78701",
        "shipping_address": "9 Elm Ct, Austin, TX 78701", "billing_country": "US", "ip_country": "US",
        "prior_orders": 7, "carrier": "USPS", "tracking_number": "9400 1118 9922 3456 7812 33",
        "delivered_at": "2026-10-09", "signature": False,
        "messages": ["Oct 21: 'Is this charge from you? I don't remember ordering.'"],
    },
}
