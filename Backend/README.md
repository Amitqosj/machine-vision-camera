# Backend

This folder contains the Python backend API for the machine vision system.

## Run Backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py --config ../config/config.yaml
```

Backend URL:

- `http://127.0.0.1:8000`

API docs:

- `http://127.0.0.1:8000/docs`

