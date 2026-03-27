# Frontend Information

## Frontend Framework and Stack

Frontend is built using **React + Vite**.

Used technologies:

- **React 18**: component-based UI for dashboard controls and live monitoring.
- **Vite**: fast development server and production build tooling.
- **Plain CSS** (`src/styles.css`): industrial-style layout and responsive panels.
- **Fetch API**: calls backend FastAPI endpoints for control and status updates.

## Why React + Vite

- React makes dashboard components modular and easy to scale.
- Vite gives very fast startup/hot reload and easy local development.
- This architecture separates UI concerns from machine-vision backend logic.

## Frontend Entry

- Main UI file: `frontend/src/App.jsx`
- Start command:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- `http://127.0.0.1:5173`

## Backend APIs Consumed by Frontend

- `GET /api/status`
- `GET /api/config`
- `GET /api/failures/recent`
- `GET /api/results/recent`
- `GET /api/stream.mjpg`
- `POST /api/control/start`
- `POST /api/control/stop`
- `POST /api/control/reset-counters`
- `POST /api/control/capture-snapshot`
- `POST /api/control/export-csv`
- `POST /api/control/save-config`
- `POST /api/roi`
- `GET /api/images/{inspection_id}`

## UI Features in Frontend

- Live MJPEG stream preview
- Start/Stop inspection buttons
- Counter cards (total/pass/fail)
- ROI update form
- Snapshot, export, and save-config actions
- Recent failed records with images
- Recent inspection table

