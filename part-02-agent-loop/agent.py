import argparse
import json
import math
import operator
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from openai import APIConnectionError, APIStatusError, OpenAI

# --- Інструменти: опис для моделі і функція Python в одному місці ------------------------

OPERATIONS = {
    "add": operator.add,
    "subtract": operator.sub,
    "multiply": operator.mul,
    "divide": operator.truediv,
    "power": operator.pow,
    "mod": operator.mod,
}


def calculate(data: dict) -> dict:
    operation, a, b = data["operation"], data["a"], data["b"]
    if operation not in OPERATIONS:
        return {"ok": False, "error": "Невідома арифметична операція."}
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in (a, b)):
        return {"ok": False, "error": "a та b мають бути скінченними числами."}
    if operation == "power" and abs(b) > 1000:
        return {"ok": False, "error": "Показник степеня завеликий."}
    try:
        result = OPERATIONS[operation](a, b)
    except ZeroDivisionError:
        return {"ok": False, "error": "Ділення на нуль."}
    except OverflowError:
        return {"ok": False, "error": "Число виходить за підтримуваний діапазон."}
    if isinstance(result, complex) or (isinstance(result, float) and not math.isfinite(result)):
        return {"ok": False, "error": "Результат не є скінченним дійсним числом."}
    return {"ok": True, "result": result}


def current_time(data: dict) -> dict:
    zone = data["timezone"]
    if zone not in available_timezones():
        return {"ok": False, "error": f"Невідомий часовий пояс: {zone}. Приклад: Europe/Kyiv."}
    try:
        now = datetime.now(ZoneInfo(zone))
    except ZoneInfoNotFoundError:
        return {"ok": False, "error": f"Невідомий часовий пояс: {zone}."}
    return {"ok": True, "timezone": zone, "iso": now.isoformat(timespec="seconds"),
            "weekday": now.strftime("%A")}


TOOLS = {
    "calculate": {
        "function": calculate,
        "description": "Apply one arithmetic operation to two numbers, in order a then b.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": list(OPERATIONS)},
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["operation", "a", "b"],
            "additionalProperties": False,
        },
    },
    "current_time": {
        "function": current_time,
        "description": "Current local date and time in an IANA time zone, e.g. Europe/Kyiv.",
        "parameters": {
            "type": "object",
            "properties": {"timezone": {"type": "string"}},
            "required": ["timezone"],
            "additionalProperties": False,
        },
    },
}


def tool_specs() -> list[dict]:
    return [{"type": "function", "name": name, "description": tool["description"],
             "parameters": tool["parameters"], "strict": True} for name, tool in TOOLS.items()]


def run_tool(name: str, arguments: str) -> dict:
    """Модель обирає інструмент і аргументи; Python перевіряє все знову і виконує."""
    tool = TOOLS.get(name)
    if tool is None:
        return {"ok": False, "error": f"Немає інструмента {name}."}
    try:
        data = json.loads(arguments)
    except json.JSONDecodeError:
        return {"ok": False, "error": "Некоректний JSON."}
    expected = set(tool["parameters"]["required"])
    if not isinstance(data, dict) or set(data) != expected:
        return {"ok": False, "error": f"Очікую поля: {', '.join(sorted(expected))}."}
    return tool["function"](data)


# --- Цикл агента: модель → інструменти → результати → модель, доки не відповість ----------

MAX_STEPS = 6            # запитів до моделі за одне завдання
MAX_TOOL_CALLS = 8       # викликів інструментів за одне завдання
MAX_TOKENS = 20_000      # сумарно вхідних і вихідних токенів за одне завдання

INSTRUCTIONS = (
    "Відповідай українською. Для обчислень і для поточного часу користуйся інструментами, "
    "не рахуй і не вгадуй сам. Якщо інструмент повернув помилку, поясни її. "
    "Коли все потрібне вже є, дай коротку фінальну відповідь без виклику інструментів."
)


class StopRun(Exception):
    """Цикл зупиняє код, а не модель: перевищено ліміт або модель ходить по колу."""


def run(client, model: str, question: str, log=print) -> str:
    seen: set[tuple[str, str]] = set()
    tokens = tool_calls = 0
    previous_id = None
    next_input: object = question

    for step in range(1, MAX_STEPS + 1):
        response = client.responses.create(
            model=model,
            instructions=INSTRUCTIONS,
            input=next_input,
            tools=tool_specs(),
            tool_choice="auto",
            parallel_tool_calls=False,
            previous_response_id=previous_id,
            store=True,
        )
        tokens += response.usage.input_tokens + response.usage.output_tokens
        if response.status != "completed":
            raise StopRun(f"Крок {step}: відповідь моделі не завершена ({response.status}).")

        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            text = response.output_text.strip()
            if not text:
                raise StopRun(f"Крок {step}: модель не дала ні виклику, ні відповіді.")
            log(f"[крок {step}] відповідь, токенів за завдання: {tokens}")
            return text

        outputs = []
        for call in calls:
            tool_calls += 1
            key = (call.name, call.arguments)
            if key in seen:
                raise StopRun(f"Крок {step}: повтор того самого виклику {call.name} {call.arguments}.")
            seen.add(key)
            result = run_tool(call.name, call.arguments)
            log(f"[крок {step}] {call.name} {call.arguments} -> {json.dumps(result, ensure_ascii=False)}")
            outputs.append({"type": "function_call_output", "call_id": call.call_id,
                            "output": json.dumps(result, ensure_ascii=False, allow_nan=False)})

        if tool_calls > MAX_TOOL_CALLS:
            raise StopRun(f"Ліміт викликів інструментів: {MAX_TOOL_CALLS}.")
        if tokens > MAX_TOKENS:
            raise StopRun(f"Ліміт токенів: {tokens} > {MAX_TOKENS}.")
        previous_id = response.id
        next_input = outputs

    raise StopRun(f"Ліміт кроків: {MAX_STEPS}, а фінальної відповіді немає.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Агент із кількома інструментами та циклом.")
    parser.add_argument("question", help="Завдання для агента.")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY", "").strip():
        parser.exit(1, "Задайте OPENAI_API_KEY у поточному терміналі.\n")
    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    try:
        with OpenAI(timeout=30.0) as client:
            print(run(client, model, args.question))
    except StopRun as stop:
        parser.exit(2, f"Зупинено: {stop}\n")
    except APIConnectionError:
        parser.exit(1, "Не вдалося з'єднатися з OpenAI API.\n")
    except APIStatusError as error:
        parser.exit(1, f"OpenAI API повернув HTTP {error.status_code}.\n")


if __name__ == "__main__":
    main()
