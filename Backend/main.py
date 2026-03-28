"""Entry point for local machine-vision backend APIs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from local_api import create_backend_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Machine Vision local backend server")
    parser.add_argument(
        "--config",
        type=str,
        default="../config/config.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("MVS_HOST", "127.0.0.1"),
        help="Host to bind backend server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MVS_PORT", "8000")),
        help="Port to bind backend server",
    )
    return parser.parse_args()


def resolve_config_path(config_arg: str) -> Path:
    config_path = Path(config_arg)
    if not config_path.is_absolute():
        config_path = (CURRENT_DIR / config_path).resolve()
    return config_path


if __name__ == "__main__":
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    app = create_backend_app(
        config_path=resolve_config_path(args.config),
        project_root=PROJECT_ROOT,
    )
    uvicorn.run(app, host=args.host, port=args.port, reload=False)

