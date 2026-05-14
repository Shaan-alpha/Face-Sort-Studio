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


class Config:
    VERSION = "2.1.1"
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

    # ── Max upload size (50 MB) ──────────────────────────────────
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
