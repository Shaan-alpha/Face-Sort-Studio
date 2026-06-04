"""
Face Sort Studio — Configuration
=================================
All paths, thresholds, and tunables live here so every other
module imports from one place.
"""

import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # Running as a bundled EXE - save data next to the EXE
    BASE_DIR = Path(sys.executable).parent
else:
    # Running in development - save data in project root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"


def _read_version() -> str:
    """Read the project version from the VERSION file (single source of truth)."""
    candidates = [
        BASE_DIR / "VERSION",
        Path(__file__).resolve().parent.parent.parent / "VERSION",
    ]
    for path in candidates:
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return "2.1.4"  # fallback if VERSION file isn't bundled (e.g. some EXE builds)


class Config:
    VERSION = _read_version()
    SECRET_KEY = os.environ.get("SECRET_KEY", "face-sort-studio-dev-key")
    PUBLIC_SHARE_MODE = os.environ.get(
        "FACE_SORT_PUBLIC_SHARE_MODE", ""
    ).lower() in {"1", "true", "yes", "on"}

    # ── Database ─────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{DATA_DIR / 'database' / 'face_sort_studio.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── File paths ───────────────────────────────────────────────
    JOBS_DIR = str(DATA_DIR / "jobs")
    OUTPUTS_DIR = str(DATA_DIR / "outputs")
    MODELS_DIR = str(DATA_DIR / "models")
    UPLOAD_DIR = str(DATA_DIR / "jobs")

    # ── Face engine defaults ─────────────────────────────────────
    DEFAULT_THRESHOLD = 0.38
    DEFAULT_MATCH_MODE = "any"
    FACE_DETECT_SIZE = (300, 300)
    FACE_SCORE_THRESHOLD = 0.9
    NMS_THRESHOLD = 0.3

    # ── Allowed image extensions ─────────────────────────────────
    ALLOWED_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".bmp",
        ".webp", ".tif", ".tiff",
    }

    # ── Model file names ─────────────────────────────────────────
    YUNET_MODEL = "face_detection_yunet_2023mar.onnx"
    SFACE_MODEL = "face_recognition_sface_2021dec.onnx"

    # ── Max upload size ──────────────────────────────────────────
    # A real photo batch easily exceeds a few-MB cap, and an oversized body
    # surfaces in the browser as a confusing "network error". Local desktop
    # use gets a generous cap; public-share mode stays tighter to limit abuse.
    # Override with FACE_SORT_MAX_UPLOAD_MB (megabytes) if needed.
    _DEFAULT_MAX_UPLOAD_MB = 200 if PUBLIC_SHARE_MODE else 2048
    MAX_CONTENT_LENGTH = int(
        os.environ.get("FACE_SORT_MAX_UPLOAD_MB", _DEFAULT_MAX_UPLOAD_MB)
    ) * 1024 * 1024
