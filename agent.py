import argparse
import json
import math
import operator
import os

from openai import APIConnectionError, APIStatusError, OpenAI

OPERATIONS = {
    "add": operator.add,
    "subtract": operator.sub,
    "multiply": operator.mul,
    "divide": operator.truediv,
}

CALCULATOR = {
    "type": "function",
    "name": "calculate",
    "description": "Apply one arithmetic operation to two numbers, in order a then b.",
    "strict": True,
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
}


def calculate(arguments: str) -> dict:
    try:
        data = json.loads(arguments)
        if not isinstance(data, dict) or data.keys() != {"operation", "a", "b"}:
            raise ValueError("Очікую поля operation, a та b.")

        operation, a, b = data["operation"], data["a"], data["b"]
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise ValueError("Невідома арифметична операція.")
        if any(type(value) not in (int, float) or not math.isfinite(value)
               for value in (a, b)):
            raise ValueError("a та b мають бути скінченними числами.")

        result = OPERATIONS[operation](a, b)
        if not math.isfinite(result):
            raise OverflowError
        return {"ok": True, "result": result}
    except ZeroDivisionError:
        return {"ok": False, "error": "Ділення на нуль."}
    except OverflowError:
        return {"ok": False, "error": "Число виходить за підтримуваний діапазон."}
    except json.JSONDecodeError:
        return {"ok": False, "error": "Некоректний JSON."}
    except ValueError as error:
        return {"ok": False, "error": str(error)}


def run(client: OpenAI, model: str, question: str) -> str:
    instructions = (
        "Відповідай українською. Виконай одну арифметичну дію над "
        "двома числами з запиту. У фінальній відповіді спирайся на "
        "результат калькулятора. Якщо він повернув помилку, поясни її."
    )
    first = client.responses.create(
        model=model,
        instructions=instructions,
        input=question,
        tools=[CALCULATOR],
        tool_choice={"type": "function", "name": "calculate"},
        parallel_tool_calls=False,
        store=True,
    )
    calls = [item for item in first.output if item.type == "function_call"]
    if first.status != "completed" or len(calls) != 1 or calls[0].name != "calculate":
        raise RuntimeError("Очікував один завершений виклик calculate.")

    call = calls[0]
    output = json.dumps(calculate(call.arguments), ensure_ascii=False, allow_nan=False)
    print(f"Виклик {call.name} {call.arguments}")
    print(f"Результат калькулятора {output}")

    final = client.responses.create(
        model=model,
        instructions=instructions,
        previous_response_id=first.id,
        input=[{
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": output,
        }],
        tools=[CALCULATOR],
        tool_choice="none",
    )
    if final.status != "completed" or not final.output_text.strip():
        raise RuntimeError("Модель не повернула завершеної текстової відповіді.")
    return final.output_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool Calling із калькулятором.")
    parser.add_argument("question", help="Одна арифметична дія над двома числами.")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY", "").strip():
        parser.exit(1, "Задайте OPENAI_API_KEY у поточному терміналі.\n")

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    try:
        with OpenAI(timeout=30.0) as client:
            print(run(client, model, args.question))
    except APIConnectionError:
        parser.exit(1, "Не вдалося з'єднатися з OpenAI API.\n")
    except APIStatusError as error:
        parser.exit(1, f"OpenAI API повернув HTTP {error.status_code}.\n")
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
