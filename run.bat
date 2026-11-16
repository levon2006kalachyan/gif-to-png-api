@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run: python -m venv .venv
    echo Then install: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

.venv\Scripts\python.exe -m src.api.server --host 127.0.0.1 --port 8765 --username admin --password admin123 %*
