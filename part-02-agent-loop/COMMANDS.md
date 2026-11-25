# Частина 2 — кілька інструментів і цикл агента: команди

Усі команди тут можна копіювати як є. Потрібен Python 3.12+ і ключ OpenAI API з доступом до моделі `gpt-5.4-mini`
(інша модель — через змінну `OPENAI_MODEL`).

## 1. Віртуальне середовище й залежності

Linux / macOS (bash):

```bash
cd part-02-agent-loop
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd part-02-agent-loop
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Перевірка циклу без моделі і без ключа

Підставний клієнт повертає записані відповіді; перевіряються інструменти, передача результатів і всі зупинки.

```bash
python test_loop.py
```

Очікуваний вивід: `agent loop: усі перевірки пройшли`.

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
python agent.py "Скільки буде 17 у степені 3 за модулем 50, і котра зараз година в Києві?"
```

Кожен крок пишеться рядком `[крок N] інструмент аргументи -> результат`, останній рядок — відповідь моделі.
Якщо агента зупинив код (ліміт кроків, викликів, токенів або повтор того самого виклику), він пише
`Зупинено: …` і виходить з кодом 2:

```bash
python agent.py "..."; echo "exit=$?"
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
| `Зупинено: …` (код 2) | агента зупинив ліміт у коді; ліміти — `MAX_STEPS`, `MAX_TOOL_CALLS`, `MAX_TOKENS` у agent.py |
