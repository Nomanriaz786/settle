"""Dispute agent: gathers facts with tools, then submits a fight/accept verdict with an evidence draft.

It never moves money. Submitting evidence or accepting happens only after a human approves in the UI.
"""
import json
import re

MIN_FIGHT_CONFIDENCE = 0.5

SYSTEM = """You are Settle, a chargeback analyst for a small online store using Braintree.
For the dispute you are given:
1. Call get_order for the transaction, then check_evidence for the dispute reason.
2. Decide: "fight" when the evidence is strong enough to win, "accept" when it is weak or the customer has a fair complaint. Fighting a dispute you will lose costs the merchant time and fees, so only fight when your confidence is at least 0.5.
3. Call submit_verdict. evidence_text is the reply to the card network: factual, polite, under 1200 characters, and it may only state facts that appeared in tool results. Never invent tracking numbers, dates or messages. When fighting, cite the order amount, items, carrier, tracking number and delivery date if known. Confidence is your honest estimate and never above 0.95, because no dispute is certain.
Write reasons for the merchant in plain English, one short sentence each."""

TOOL_SPECS = {
    "get_order": {
        "description": "Get the shop's order record (customer, items, addresses, shipping, messages) for a Braintree transaction.",
        "parameters": {"type": "object", "properties": {"transaction_id": {"type": "string"}},
                       "required": ["transaction_id"], "additionalProperties": False},
    },
    "check_evidence": {
        "description": "Check which pieces of evidence card networks expect for this dispute reason are present for the order.",
        "parameters": {"type": "object",
                       "properties": {"transaction_id": {"type": "string"}, "reason": {"type": "string"}},
                       "required": ["transaction_id", "reason"], "additionalProperties": False},
    },
    "get_customer_history": {
        "description": "List the customer's other orders with this shop, to judge whether they are a real repeat buyer.",
        "parameters": {"type": "object", "properties": {"email": {"type": "string"}},
                       "required": ["email"], "additionalProperties": False},
    },
}

VERDICT_SPEC = {
    "description": "Submit the final recommendation for the merchant to approve.",
    "parameters": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["fight", "accept"]},
            "confidence": {"type": "number", "description": "0 to 1, chance of winning if fought"},
            "reasons": {"type": "array", "items": {"type": "string"}},
            "evidence_text": {"type": "string", "description": "Reply to the card network; empty if accepting"},
        },
        "required": ["verdict", "confidence", "reasons", "evidence_text"],
        "additionalProperties": False,
    },
}


class AgentError(Exception):
    pass


class Agent:
    def __init__(self, llm, model, tools, max_steps=8):
        self.llm, self.model, self.tools, self.max_steps = llm, model, tools, max_steps

    def _specs(self):
        specs = {name: TOOL_SPECS[name] for name in self.tools if name in TOOL_SPECS}
        specs["submit_verdict"] = VERDICT_SPEC
        return [{"type": "function", "function": {"name": n, **s}} for n, s in specs.items()]

    def run(self, dispute, on_step=lambda step: None):
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": "New dispute:\n" + json.dumps(dispute)}]
        steps = []
        for _ in range(self.max_steps):
            msg = self.llm.chat.completions.create(model=self.model, messages=messages,
                                                   tools=self._specs(), tool_choice="required").choices[0].message
            calls = msg.tool_calls or []
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": [{"id": c.id, "type": "function",
                                             "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                            for c in calls]})
            for call in calls:
                args = json.loads(call.function.arguments or "{}")
                if call.function.name == "submit_verdict":
                    verdict = _validate(args)
                    invented = _ungrounded(verdict["evidence_text"], [dispute] + [s["result"] for s in steps])
                    if not invented:
                        return {**verdict, "steps": steps}
                    # the model gets another try, with the exact facts it could not back up
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(
                        {"error": "evidence_text states facts that are not in any tool result: "
                                  + ", ".join(invented) + ". Remove them or use only facts from tool results."})})
                    continue
                result = self._call(call.function.name, args)
                step = {"tool": call.function.name, "args": args, "result": result}
                steps.append(step)
                on_step(step)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
        raise AgentError(f"No verdict after {self.max_steps} steps")

    def _call(self, name, args):
        if name not in self.tools:
            return {"error": f"Unknown tool {name}"}
        try:
            return self.tools[name](**args)
        except Exception as e:  # the model sees the failure and can recover
            return {"error": str(e)}


def _validate(v):
    if v.get("verdict") not in ("fight", "accept"):
        raise AgentError(f"Invalid verdict {v.get('verdict')!r}")
    v["confidence"] = max(0.0, min(0.95, float(v.get("confidence", 0))))  # no dispute is certain
    if v["verdict"] == "fight" and v["confidence"] < MIN_FIGHT_CONFIDENCE:
        v.update(verdict="accept", evidence_text="", reasons=[*v.get("reasons", []),
                 "Settle changed this to accept because the chance of winning is below 50%."])
    return v


# Facts a reviewer can check: ISO dates, money amounts, and ids/tracking numbers mixing letters and digits.
# shortcut: all-digit tracking numbers written with spaces are not checked; add a carrier-format parser if needed.
FACT = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d+\.\d{2}\b|\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{6,}\b")


def _ungrounded(text, sources):
    known = re.sub(r"\s", "", json.dumps(sources, default=str)).upper()
    return [f for f in dict.fromkeys(FACT.findall(text or "")) if f.upper() not in known]
