"""
Face Sort Studio — Entry Point
================================
Run directly:   python run.py
Or via Flask:   flask --app run:app run --reload
"""

import os

from face_sort.app.main import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FACE_SORT_HOST", "0.0.0.0")
    port = int(os.environ.get("FACE_SORT_PORT", "8000"))
    debug = os.environ.get("FACE_SORT_DEBUG", "").lower() in {
        "1", "true", "yes", "on"
    }
    app.run(host=host, port=port, debug=debug)
