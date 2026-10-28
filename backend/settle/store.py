"""SQLite store for the demo shop's order records and the agent's saved analyses."""
import json
import sqlite3


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS orders (transaction_id TEXT PRIMARY KEY, data TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS analyses (dispute_id TEXT PRIMARY KEY, data TEXT)")

    def save_order(self, order):
        self._put("orders", "transaction_id", order["transaction_id"], order)

    def get_order(self, transaction_id):
        return self._get("orders", "transaction_id", transaction_id)

    def orders_by_email(self, email):
        rows = self.db.execute("SELECT data FROM orders WHERE lower(json_extract(data, '$.email')) = lower(?)", (email,))
        return [json.loads(r[0]) for r in rows]

    def save_analysis(self, dispute_id, analysis):
        self._put("analyses", "dispute_id", dispute_id, analysis)

    def get_analysis(self, dispute_id):
        return self._get("analyses", "dispute_id", dispute_id)

    def _put(self, table, key, value, data):
        self.db.execute(f"INSERT OR REPLACE INTO {table} ({key}, data) VALUES (?, ?)", (value, json.dumps(data)))
        self.db.commit()

    def _get(self, table, key, value):
        row = self.db.execute(f"SELECT data FROM {table} WHERE {key} = ?", (value,)).fetchone()
        return json.loads(row[0]) if row else None
