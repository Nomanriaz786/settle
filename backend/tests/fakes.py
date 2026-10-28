"""Scripted stand-in for the OpenAI client: returns queued assistant messages in order."""
import json
from types import SimpleNamespace as NS


def tool_call(name, args, call_id="c1"):
    return NS(id=call_id, type="function", function=NS(name=name, arguments=json.dumps(args)))


class FakeLLM:
    def __init__(self, *messages):
        self.queue = list(messages)
        self.calls = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        msg = self.queue.pop(0)
        return NS(choices=[NS(message=NS(content=msg.get("content"), tool_calls=msg.get("tool_calls"),
                                         role="assistant"))])
