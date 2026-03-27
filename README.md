# Machine Vision Inspection System

Production-ready real-time inspection platform with:

- Python backend service in `Backend`
- React + Vite web dashboard in `frontend`
- Reusable machine vision core in `app`

## Updated Architecture

- `app`: core camera/inspection/pipeline/services modules (shared backend logic)
- `Backend`: FastAPI backend entrypoint and API wiring
- `frontend`: React web dashboard to control and monitor inspection
- `config/config.yaml`: centralized runtime configuration
- `data/`: logs, images, exports, database

## Project Structure

```text
machine vision camera/
├── Backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── README.md
│   └── BACKEND_INFO.md
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── .env.example
│   ├── FRONTEND_INFO.md
│   ├── index.html
│   ├── package.json
│   ├── README.md
│   └── vite.config.js
├── app/
│   ├── camera/
│   ├── core/
│   ├── db/
│   ├── inspection/
│   ├── pipeline/
│   ├── services/
│   ├── ui/                 # legacy desktop UI (optional)
│   └── utils/
├── config/
│   └── config.yaml
├── data/
├── docs/
├── tests/
├── main.py                 # legacy desktop entrypoint (optional)
└── requirements.txt
```

## Run Backend (Python)

```powershell
cd "Backend"
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py --config ../config/config.yaml
```

Backend starts at:

- `http://127.0.0.1:8000`

## Run Frontend (React + Vite)

```powershell
cd "frontend"
npm install
npm run dev
```

Frontend starts at:

- `http://127.0.0.1:5173`

Vite proxy already forwards `/api` and `/health` to backend.

## Main Backend API Endpoints

- `GET /health`
- `GET /api/config`
- `GET /api/status`
- `GET /api/stream.mjpg`
- `GET /api/results/recent`
- `GET /api/failures/recent`
- `GET /api/images/{inspection_id}`
- `POST /api/control/start`
- `POST /api/control/stop`
- `POST /api/control/reset-counters`
- `POST /api/control/capture-snapshot`
- `POST /api/control/export-csv`
- `POST /api/control/save-config`
- `POST /api/roi`

## Data + Database

- Default DB: `sqlite:///data/inspection.db`
- Failed images: `data/failed/...`
- Optional pass images: `data/passed/...`
- CSV exports: `data/exports/...`
- Logs: `data/logs/*.log`

Schema reference: `docs/database_schema.sql`

## Testing (Python Core)

From project root:

```powershell
python -m pytest -q
```

## Notes

- If no physical camera is available, backend falls back to simulated feed when `simulate_on_failure: true`.
- Legacy desktop UI still exists (`main.py` + `app/ui`), but the primary operator dashboard is now `frontend`.

