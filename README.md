Фиксация зависимостей:
```pip freeze > requirements.txt```

Восстановление окружения:
```commandline
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```