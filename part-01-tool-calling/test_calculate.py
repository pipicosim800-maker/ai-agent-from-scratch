"""Local check of the calculator tool: no API key, no network.

Run from this folder:  python test_calculate.py
"""
import json

from agent import calculate


def call(operation, a, b):
    return calculate(json.dumps({"operation": operation, "a": a, "b": b}))


assert call("multiply", 17, 23) == {"ok": True, "result": 391}
assert call("add", 2, 3) == {"ok": True, "result": 5}
assert call("subtract", 2, 3) == {"ok": True, "result": -1}
assert call("divide", 1, 4) == {"ok": True, "result": 0.25}
assert call("divide", 1, 0) == {"ok": False, "error": "Ділення на нуль."}
assert call("power", 2, 3)["ok"] is False                      # not on the whitelist
assert calculate("not json") == {"ok": False, "error": "Некоректний JSON."}
assert calculate('{"operation": "add", "a": 1}')["ok"] is False  # a missing field
assert call("add", "1", 2)["ok"] is False                      # a string is not a number
assert call("multiply", 1e308, 10)["ok"] is False              # overflow
print("calculate: усі перевірки пройшли")
