import pytest

from settle.agent import Agent, AgentError
from tests.fakes import FakeLLM, tool_call

DISPUTE = {"id": "d1", "transaction_id": "tx1", "reason": "fraud", "amount": "49.00", "reply_by": "2026-10-30"}
VERDICT = {"verdict": "fight", "confidence": 0.8, "reasons": ["Delivered to billing address"],
           "evidence_text": "The order was delivered to the cardholder's billing address."}


def test_runs_requested_tools_then_returns_verdict():
    seen = []
    llm = FakeLLM({"tool_calls": [tool_call("get_order", {"transaction_id": "tx1"})]},
                  {"tool_calls": [tool_call("submit_verdict", VERDICT, "c2")]})
    agent = Agent(llm, "m", {"get_order": lambda transaction_id: seen.append(transaction_id) or {"ok": 1}})
    result = agent.run(DISPUTE)
    assert seen == ["tx1"]
    assert result["verdict"] == "fight"
    assert [s["tool"] for s in result["steps"]] == ["get_order"]


def test_tool_result_is_sent_back_to_the_model():
    llm = FakeLLM({"tool_calls": [tool_call("get_order", {"transaction_id": "tx1"})]},
                  {"tool_calls": [tool_call("submit_verdict", VERDICT, "c2")]})
    Agent(llm, "m", {"get_order": lambda transaction_id: {"customer_name": "Ana"}}).run(DISPUTE)
    tool_msgs = [m for m in llm.calls[1]["messages"] if m.get("role") == "tool"]
    assert "Ana" in tool_msgs[0]["content"]


def test_unknown_tool_is_reported_to_model_not_crash():
    llm = FakeLLM({"tool_calls": [tool_call("refund_everything", {})]},
                  {"tool_calls": [tool_call("submit_verdict", VERDICT, "c2")]})
    result = Agent(llm, "m", {}).run(DISPUTE)
    assert result["verdict"] == "fight"
    assert "unknown tool" in llm.calls[1]["messages"][-1]["content"].lower()


def test_gives_up_after_max_steps():
    llm = FakeLLM(*[{"tool_calls": [tool_call("get_order", {"transaction_id": "tx1"}, f"c{i}")]} for i in range(10)])
    with pytest.raises(AgentError):
        Agent(llm, "m", {"get_order": lambda transaction_id: {}}, max_steps=3).run(DISPUTE)


def test_rejects_invalid_verdict():
    llm = FakeLLM({"tool_calls": [tool_call("submit_verdict", {**VERDICT, "verdict": "refund_all"})]})
    with pytest.raises(AgentError):
        Agent(llm, "m", {}).run(DISPUTE)


def test_on_step_callback_sees_each_step():
    steps = []
    llm = FakeLLM({"tool_calls": [tool_call("get_order", {"transaction_id": "tx1"})]},
                  {"tool_calls": [tool_call("submit_verdict", VERDICT, "c2")]})
    Agent(llm, "m", {"get_order": lambda transaction_id: {}}).run(DISPUTE, on_step=steps.append)
    assert steps[0]["tool"] == "get_order"
