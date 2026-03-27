# System Architecture

## Runtime Flow

1. Camera provider (`app/camera`) captures frames.
2. Capture thread pushes `FramePacket` into bounded queue.
3. Processing thread pulls frames and runs `InspectionEngine`.
4. `InspectionService` saves images + decisions to DB and updates runtime counters.
5. FastAPI backend (`Backend/main.py`) exposes control/status/stream endpoints.
6. React UI (`frontend`) consumes backend API for operations and monitoring.

## Separation of Concerns

- `app/core`: config, logging, shared exceptions, runtime state
- `app/camera`: hardware abstraction (webcam now, SDK-ready later)
- `app/inspection`: pluggable strategy chain and decision model
- `app/pipeline`: producer-consumer threading + queue/drop policy
- `app/db`: ORM models and repository
- `app/services`: orchestration, image storage, CSV export, runtime coordination
- `Backend`: FastAPI web backend and API contract
- `frontend`: React + Vite operator dashboard
- `app/ui`: legacy PySide6 desktop dashboard (optional)

## Real-Time Design Notes

- Capture and processing are isolated into separate daemon threads.
- Queue size and frame drop policy are configurable.
- On camera failure, reconnect attempts are automatic.
- Optional simulated camera fallback preserves system operability without hardware.
- Backend supports MJPEG stream and HTTP control endpoints for web clients.

