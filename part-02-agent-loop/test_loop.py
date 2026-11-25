"""The agent loop without a model and without a key: a fake client plays scripted replies.

Run from this folder:  python test_loop.py
"""
import json
from types import SimpleNamespace as NS

import agent
from agent import StopRun, run, run_tool


def call(name, args, call_id):
    return NS(type="function_call", name=name, arguments=json.dumps(args), call_id=call_id)


def reply(rid, *calls, text="", tokens=100):
    return NS(id=rid, status="completed", output=list(calls), output_text=text,
              usage=NS(input_tokens=tokens, output_tokens=0))


class FakeClient:
    """Returns the scripted replies in order and records every request."""
    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.responses = self

    def create(self, **request):
        self.requests.append(request)
        return self.replies.pop(0)


silent = lambda *_: None

# 1. Two tools, then an answer: the loop feeds each result back and stops on plain text.
client = FakeClient(
    reply("r1", call("calculate", {"operation": "multiply", "a": 17, "b": 23}, "c1")),
    reply("r2", call("current_time", {"timezone": "Europe/Kyiv"}, "c2")),
    reply("r3", text="17 × 23 = 391; у Києві зараз …"),
)
assert run(client, "m", "Скільки 17×23 і котра година в Києві?", log=silent).startswith("17 × 23 = 391")
assert [r["previous_response_id"] for r in client.requests] == [None, "r1", "r2"]
first_result = client.requests[1]["input"][0]
assert first_result["call_id"] == "c1" and json.loads(first_result["output"]) == {"ok": True, "result": 391}
assert client.requests[0]["tool_choice"] == "auto"

# 2. The same call twice: code stops the run, the model does not get a third try.
client = FakeClient(
    reply("r1", call("calculate", {"operation": "add", "a": 1, "b": 2}, "c1")),
    reply("r2", call("calculate", {"operation": "add", "a": 1, "b": 2}, "c2")),
)
try:
    run(client, "m", "x", log=silent)
    raise AssertionError("a repeated call must stop the run")
except StopRun as stop:
    assert "повтор" in str(stop)

# 3. A model that never answers: the step limit ends it.
client = FakeClient(*[reply(f"r{i}", call("calculate", {"operation": "add", "a": i, "b": 0}, f"c{i}"))
                      for i in range(agent.MAX_STEPS + 1)])
try:
    run(client, "m", "x", log=silent)
    raise AssertionError("the step limit must stop the run")
except StopRun as stop:
    assert "кроків" in str(stop) and len(client.requests) == agent.MAX_STEPS

# 4. The token budget ends it too.
client = FakeClient(reply("r1", call("calculate", {"operation": "add", "a": 1, "b": 1}, "c1"),
                          tokens=agent.MAX_TOKENS + 1))
try:
    run(client, "m", "x", log=silent)
    raise AssertionError("the token budget must stop the run")
except StopRun as stop:
    assert "токенів" in str(stop)

# 5. Errors are data the model reads, never exceptions.
assert run_tool("delete_files", "{}")["ok"] is False
assert run_tool("calculate", "not json") == {"ok": False, "error": "Некоректний JSON."}
assert run_tool("calculate", '{"operation": "add", "a": 1, "b": 2, "c": 3}')["ok"] is False
assert run_tool("calculate", '{"operation": "divide", "a": 1, "b": 0}') == {"ok": False, "error": "Ділення на нуль."}
assert run_tool("calculate", '{"operation": "power", "a": 2, "b": 10}') == {"ok": True, "result": 1024}
assert run_tool("calculate", '{"operation": "power", "a": 10, "b": 100000}')["ok"] is False
assert run_tool("calculate", '{"operation": "power", "a": -8, "b": 0.5}')["ok"] is False
assert run_tool("calculate", '{"operation": "mod", "a": 17, "b": 5}') == {"ok": True, "result": 2}
assert run_tool("current_time", '{"timezone": "Mars/Olympus"}')["ok"] is False
assert run_tool("current_time", '{"timezone": "Europe/Kyiv"}')["ok"] is True
print("agent loop: усі перевірки пройшли")
