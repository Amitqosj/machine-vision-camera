# Windows Deployment Notes

## Recommended Environment

- Windows 10/11
- Python 3.11 or 3.12 (64-bit)
- Local camera driver installed and tested in Windows Camera app

## Build Standalone EXE (PyInstaller)

Install build tools:

```powershell
python -m pip install pyinstaller
```

Create executable:

```powershell
pyinstaller --noconfirm --clean --name machine-vision-inspector --windowed ^
  --add-data "config;config" ^
  --add-data "data;data" ^
  main.py
```

Output artifact:

- `dist/machine-vision-inspector/machine-vision-inspector.exe`

## Runtime Checklist

- Ensure `config/config.yaml` is present next to executable bundle.
- Ensure write permissions for `data/` directory.
- For industrial deployment, configure service account with camera and filesystem access.
- Use Windows Task Scheduler or a startup script if auto-launch is needed.

