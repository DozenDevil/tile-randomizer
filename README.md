Фиксация зависимостей:
```commandline
pip freeze > requirements.txt
```

Создание исполнительного файла:
```commandline
pyinstaller --onefile --console --clean --collect-all textual --collect-all rich --name dnd_tiles --icon assets/icon.ico main.py
```

Восстановление окружения:
```commandline
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```