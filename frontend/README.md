# Frontend (React + Vite)

## Start Development UI

```powershell
cd frontend
npm install
npm run dev
```

Vite runs on:

- `http://127.0.0.1:5173`

## Notes

- The frontend proxies `/api` and `/health` to `http://127.0.0.1:8000`.
- Ensure backend is running from `Backend/main.py`.
- Optionally set `VITE_API_BASE` in `.env` if you want direct API URLs without proxy.

