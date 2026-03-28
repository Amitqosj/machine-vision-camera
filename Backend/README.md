# Backend

This folder contains the FastAPI backend launcher used for local use and EXE packaging.

## Run Backend (Python)

```powershell
cd Backend
py -3 -m pip install -r requirements.txt
py main.py
```

Backend URL:

- `http://127.0.0.1:8000`

Health endpoint:

- `http://127.0.0.1:8000/api/health`

## Build EXE (PyInstaller)

```powershell
cd Backend
.\build_exe.ps1
```

Output:

- `Backend\dist\machine-vision-backend.exe`

## Share EXE

1. Copy `machine-vision-backend.exe` from `Backend\dist`.
2. Send it to the user (zip is recommended).
3. User runs the EXE (double-click or terminal).
4. Backend starts on `http://127.0.0.1:8000`.
5. Browser opens your deployed frontend: `https://machine-vision-camera.onrender.com/`.

## Optional Environment Variables

- `MVS_FRONTEND_URL` (default `https://machine-vision-camera.onrender.com/`)
- `MVS_HOST` (default `127.0.0.1`)
- `MVS_PORT` (default `8000`)
- `MVS_OPEN_BROWSER` (`1` default, set `0` to disable auto-open)

