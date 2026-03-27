# Backend Information

## Backend Framework and Stack

Yes, backend is built using **FastAPI**.

Used technologies:

- **FastAPI**: Web API framework for backend endpoints.
- **Uvicorn**: ASGI server to run FastAPI app.
- **OpenCV (`cv2`)**: Camera frames, image encoding, stream generation.
- **NumPy**: Image array operations.
- **Pydantic**: Request/response and configuration data models.
- **SQLAlchemy**: Database ORM for inspection result storage.
- **SQLite (default)** / **PostgreSQL (optional)**: persistent database.
- **PyYAML**: YAML config loading from `config/config.yaml`.
- **python-dotenv**: environment variable loading.
- **Threading + Queue** (inside shared `app` services): real-time capture and processing pipeline.

## Why These Technologies

- **FastAPI**: clean typed APIs, fast development, automatic docs (`/docs`).
- **Uvicorn**: production-grade async server for FastAPI.
- **OpenCV + NumPy**: industry-standard Python image processing stack.
- **SQLAlchemy**: maintainable DB abstraction and easy migration to PostgreSQL.
- **Pydantic + YAML**: robust config validation and readable configuration files.

## Backend Entry Point

- File: `Backend/main.py`
- Start command:

```powershell
cd Backend
python main.py --config ../config/config.yaml
```

## API Endpoints (Complete List)

### Health and Status

- `GET /health`  
  Checks service health and camera connection/running state.

- `GET /api/config`  
  Returns current camera and inspection configuration used by backend.

- `GET /api/status`  
  Returns runtime counters, DB counters, and latest inspection result.

### Inspection Control

- `POST /api/control/start`  
  Starts camera + inspection pipeline.

- `POST /api/control/stop`  
  Stops pipeline.

- `POST /api/control/reset-counters`  
  Resets runtime counters shown in dashboard.

- `POST /api/control/capture-snapshot`  
  Saves current frame to snapshot folder.

- `POST /api/control/export-csv`  
  Exports inspection history as CSV file.

- `POST /api/control/save-config`  
  Persists current in-memory config to YAML.

### ROI and Inspection Data

- `POST /api/roi`  
  Updates ROI values (`x`, `y`, `width`, `height`, `enabled`).

- `GET /api/results/recent?limit=25`  
  Returns recent inspection records (PASS and FAIL).

- `GET /api/failures/recent?limit=10`  
  Returns recent failed inspection records with image URL when available.

### Streaming and Images

- `GET /api/frame.jpg`  
  Returns latest frame as a single JPEG image.

- `GET /api/stream.mjpg`  
  Returns continuous MJPEG stream for live dashboard preview.

- `GET /api/images/{inspection_id}`  
  Returns saved failed-image file for the specified inspection ID.

