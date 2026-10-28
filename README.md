# Settle

Settle is an AI agent that fights chargebacks for small online shops. It is built on Braintree, a PayPal service, and runs entirely in the Braintree sandbox.

When a customer disputes a card payment, the merchant has only a few days to answer with the right evidence. Small shops often miss that window or send weak evidence, so they lose the sale plus a fee. Settle reads each new dispute, gathers the order facts, recommends whether to fight or accept, and drafts the evidence. A person approves before anything is sent to Braintree.

Built for the [PayPal AI Hackathon](https://paypalaihackathon.devpost.com/). The demo shop is Kiln & Co., a small ceramics store.

## What it does

- **Lists open disputes** from Braintree in an AG Grid table with the customer, amount, reason, reply-by date and the agent's verdict.
- **Analyses a dispute with an AI agent** (OpenAI function calling). The agent calls tools to pull the order and the Braintree payment record, check which evidence the dispute reason needs, and look up the customer's past orders. It returns a fight or accept recommendation in plain English plus an evidence draft.
- **Keeps a human in the loop.** Nothing touches money until you click:
  - **Submit evidence** adds the (editable) text evidence to the Braintree dispute and finalizes it.
  - **Accept** accepts the dispute in Braintree.
- **Simulates a chargeback.** Creates a real sandbox payment with Braintree's dispute test card, so a real sandbox dispute appears within a minute, paired with one of three demo orders (friendly fraud, stolen card, forgotten subscription).

## Stack

- Backend: Python 3.11+, FastAPI, the `braintree` SDK, OpenAI, SQLite for the shop's order records.
- Frontend: React and Vite, AG Grid Community.
- Braintree is the source of truth for money. SQLite only stores the demo shop's orders and saved analyses.

## Run it locally

You need a free [Braintree sandbox account](https://www.braintreepayments.com/sandbox) and an OpenAI API key.

1. Backend:
   ```bash
   cd backend
   python -m venv .venv
   # Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env    # then fill in your Braintree sandbox keys and OpenAI key
   uvicorn settle.main:app --port 8010
   ```
2. Frontend (in a second terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open http://localhost:5173 and click **Simulate a chargeback**.

To serve everything from one process, run `npm run build` in `frontend`. The backend then serves the built dashboard at http://localhost:8010.

## Tests

```bash
cd backend
pytest
```

The sandbox integration test runs only when Braintree credentials are set. All other tests use fakes and need no keys.

## License

MIT, see [LICENSE](LICENSE).
