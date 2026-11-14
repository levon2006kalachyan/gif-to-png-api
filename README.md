# GIF to PNG API

Веб-приложение с HTTP API для асинхронного преобразования файлов из формата GIF в формат PNG.

Курсовая работа. Вариант №3.

## Этап 1. Консольная утилита

Реализована консольная программа для преобразования GIF-изображений в PNG.

### Возможности

- Чтение путей к файлам через стандартный ввод.
- Преобразование GIF в PNG с помощью Pillow.
- Сохранение PNG-файла на диск.
- Обработка ошибок входных данных.
- Поддержка прозрачности изображений.
- Преобразование первого кадра анимированного GIF.

### Установка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Запуск

```powershell
python -m src.converter
```

Программа последовательно запрашивает путь к GIF-файлу и путь для сохранения PNG.

### Генерация примеров

```powershell
python examples/generate_examples.py
```

### Автоматические тесты

```powershell
python -m pytest -v
```

## Следующие этапы

**Этап 2:** HTTP API на основе `BaseHTTPRequestHandler`, XML, HTTP Basic Authentication, асинхронное выполнение задач через `subprocess`, API-клиент и Model-Based Testing с Hypothesis.

**Этап 3:** подключение SQLite с использованием SQLAlchemy и повторное тестирование HTTP API.