# Частина 1 — Tool Calling у Python: команди

Усі команди тут можна копіювати як є. Потрібен Python 3.12+ і ключ OpenAI API з доступом до моделі `gpt-5.4-mini`
(інша модель — через змінну `OPENAI_MODEL`).

## 1. Віртуальне середовище й залежності

Linux / macOS (bash):

```bash
cd part-01-tool-calling
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd part-01-tool-calling
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Перевірка калькулятора без ключа і без мережі

```bash
python test_calculate.py
```

Очікуваний вивід: `calculate: усі перевірки пройшли`.

## 3. Ключ API — лише в поточному терміналі, без запису у файл

Linux / macOS (bash) — ключ не показується під час введення:

```bash
read -r -s -p "OPENAI_API_KEY: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
```

Windows (PowerShell):

```powershell
$secure = Read-Host "OPENAI_API_KEY" -AsSecureString
$env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
Remove-Variable secure
```

Інша модель (необов'язково):

```bash
export OPENAI_MODEL=gpt-5.4-mini
```

```powershell
$env:OPENAI_MODEL = "gpt-5.4-mini"
```

## 4. Запуск

```bash
python agent.py "Помнож 17 на 23"
```

Очікуваний вивід (останній рядок формулює модель, тому він може трохи відрізнятися):

```text
Виклик calculate {"operation":"multiply","a":17,"b":23}
Результат калькулятора {"ok": true, "result": 391}
17 × 23 = 391.
```

Помилка, яку калькулятор повертає як дані, а модель пояснює:

```bash
python agent.py "Поділи 10 на 0"
```

```text
Виклик calculate {"operation":"divide","a":10,"b":0}
Результат калькулятора {"ok": false, "error": "Ділення на нуль."}
```

## 5. Прибрати ключ після роботи

```bash
unset OPENAI_API_KEY
```

```powershell
Remove-Item Env:OPENAI_API_KEY
```

## Якщо щось не так

| Повідомлення | Що перевірити |
|---|---|
| `Задайте OPENAI_API_KEY у поточному терміналі.` | крок 3 у тому самому терміналі, де запускаєте |
| `OpenAI API повернув HTTP 401.` | ключ правильний і не відкликаний |
| `OpenAI API повернув HTTP 429.` | ліміт запитів або баланс на platform.openai.com |
| `OpenAI API повернув HTTP 404.` | назва моделі в `OPENAI_MODEL` і доступ ключа до неї |
| `Не вдалося з'єднатися з OpenAI API.` | мережа або проксі |
