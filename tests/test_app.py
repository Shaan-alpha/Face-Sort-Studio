"""
Face Sort Studio — Smoke Tests
=================================
Quick tests to verify the app boots and core routes work.
Run:  python -m pytest tests/ -v
"""

import os
import sys
import io
from pathlib import Path

import numpy as np
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.main import create_app
from backend.app.database import db, Job, utc_now


@pytest.fixture
def app(tmp_path):
    """Create a test app with isolated paths and an in-memory database."""
    data_dir = tmp_path / "data"
    app = create_app({
        "TESTING": True,
        "SKIP_MODEL_BOOTSTRAP": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JOBS_DIR": str(data_dir / "jobs"),
        "OUTPUTS_DIR": str(data_dir / "outputs"),
        "MODELS_DIR": str(data_dir / "models"),
        "UPLOAD_DIR": str(data_dir / "jobs"),
    })
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def public_share_client(tmp_path):
    data_dir = tmp_path / "shared-data"
    app = create_app({
        "TESTING": True,
        "SKIP_MODEL_BOOTSTRAP": True,
        "PUBLIC_SHARE_MODE": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JOBS_DIR": str(data_dir / "jobs"),
        "OUTPUTS_DIR": str(data_dir / "outputs"),
        "MODELS_DIR": str(data_dir / "models"),
        "UPLOAD_DIR": str(data_dir / "jobs"),
    })
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


# ── Basic route tests ────────────────────────────────────────

class TestRoutes:
    def test_index_loads(self, client):
        """Home page should return 200 and contain the app title."""
        res = client.get("/")
        assert res.status_code == 200
        assert b"Face Sort Studio" in res.data

    def test_jobs_list_empty(self, client):
        """Job list should return an empty array initially."""
        res = client.get("/api/jobs")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_analytics_empty(self, client):
        """Analytics should return zero counts with no jobs."""
        res = client.get("/api/analytics")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_jobs"] == 0
        assert data["completed_jobs"] == 0
        assert data["total_photos_processed"] == 0

    def test_job_not_found(self, client):
        """Non-existent job should return 404."""
        res = client.get("/api/jobs/nonexistent-id")
        assert res.status_code == 404

    def test_create_job_no_references(self, client):
        """Creating a job without reference photos should fail."""
        res = client.post("/api/jobs", data={})
        assert res.status_code == 400

    def test_create_job_rejects_bad_match_mode(self, client):
        """Unexpected match modes should return 400."""
        res = client.post(
            "/api/jobs",
            data={
                "match_mode": "invalid",
                "gallery_path": os.getcwd(),
                "references": (io.BytesIO(b"fake"), "ref.jpg"),
            },
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_create_job_rejects_bad_threshold(self, client):
        """Threshold must be numeric and within the allowed range."""
        res = client.post(
            "/api/jobs",
            data={
                "threshold": "not-a-number",
                "gallery_path": os.getcwd(),
                "references": (io.BytesIO(b"fake"), "ref.jpg"),
            },
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_shared_mode_rejects_local_folder_paths(self, public_share_client):
        """Public share mode should force uploads instead of server-local paths."""
        res = public_share_client.post(
            "/api/jobs",
            data={
                "gallery_path": os.getcwd(),
                "references": (io.BytesIO(b"fake"), "ref.jpg"),
            },
            content_type="multipart/form-data",
        )

        assert res.status_code == 400
        assert "disabled while the app is shared publicly" in res.get_json()["error"]

    def test_create_job_queues_background_worker(
        self, app, client, monkeypatch, tmp_path
    ):
        """Successful job creation should queue the background worker with the Flask app."""
        import backend.app.main as main_module

        created_threads = []

        class FakeThread:
            def __init__(self, target, args=(), kwargs=None, daemon=None):
                self.target = target
                self.args = args
                self.kwargs = kwargs or {}
                self.daemon = daemon
                self.started = False
                created_threads.append(self)

            def start(self):
                self.started = True

        gallery_dir = tmp_path / "gallery"
        gallery_dir.mkdir()

        monkeypatch.setattr(main_module.threading, "Thread", FakeThread)

        res = client.post(
            "/api/jobs",
            data={
                "gallery_path": str(gallery_dir),
                "references": (io.BytesIO(b"fake"), "ref.jpg"),
            },
            content_type="multipart/form-data",
        )

        assert res.status_code == 202
        assert len(created_threads) == 1
        assert created_threads[0].target is main_module.run_sorting_job
        assert created_threads[0].args[0] is app
        assert created_threads[0].args[1] == res.get_json()["job_id"]
        assert created_threads[0].started is True


# ── Config tests ─────────────────────────────────────────────

class TestConfig:
    def test_allowed_extensions(self, app):
        exts = app.config.get("ALLOWED_EXTENSIONS", set())
        # If config has it, verify common types
        if exts:
            assert ".jpg" in exts
            assert ".png" in exts

    def test_data_dirs_configured(self, app):
        assert app.config.get("JOBS_DIR")
        assert app.config.get("OUTPUTS_DIR")
        assert app.config.get("MODELS_DIR")

    def test_create_app_creates_sqlite_parent_dir(self, tmp_path):
        data_dir = tmp_path / "runtime"
        db_path = data_dir / "database" / "face_sort_studio.db"

        app = create_app({
            "TESTING": True,
            "SKIP_MODEL_BOOTSTRAP": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "JOBS_DIR": str(data_dir / "jobs"),
            "OUTPUTS_DIR": str(data_dir / "outputs"),
            "MODELS_DIR": str(data_dir / "models"),
            "UPLOAD_DIR": str(data_dir / "jobs"),
        })

        assert app is not None
        assert db_path.parent.exists()
        assert db_path.exists()


# ── Face engine unit tests (import only, no model files) ─────

class TestFaceEngineImport:
    def test_can_import(self):
        """The face engine module should be importable."""
        from backend.app.services.face_engine import FaceEngine
        assert FaceEngine is not None

    def test_missing_model_raises(self, tmp_path):
        """Instantiating with a bad path should raise FileNotFoundError."""
        from backend.app.services.face_engine import FaceEngine
        with pytest.raises(FileNotFoundError):
            FaceEngine(str(tmp_path))


class TestJobRunner:
    def test_uses_app_config_runtime_paths(self, app, tmp_path, monkeypatch):
        from backend.app.services import job_runner

        job_id = "job-config-paths"
        job_dir = Path(app.config["JOBS_DIR"]) / job_id
        ref_dir = job_dir / "references"
        gallery_dir = tmp_path / "gallery"
        output_dir = Path(app.config["OUTPUTS_DIR"]) / job_id

        ref_dir.mkdir(parents=True)
        gallery_dir.mkdir()
        (ref_dir / "ref.jpg").write_bytes(b"reference")
        (gallery_dir / "gallery.jpg").write_bytes(b"gallery")

        class FakeFaceEngine:
            def __init__(self, models_dir):
                self.models_dir = models_dir

            def process_image(self, image_path):
                return [
                    (
                        np.zeros(15, dtype=np.float32),
                        np.array([1.0, 0.0], dtype=np.float32),
                    )
                ]

            def detect_faces(self, image):
                return np.array([[0.0] * 15], dtype=np.float32)

            def cluster_targets(self, embeddings, threshold=0.38):
                return [[embeddings[0]]]

            def compare(self, emb_a, emb_b):
                return 0.99

        monkeypatch.setattr(job_runner, "FaceEngine", FakeFaceEngine)

        with app.app_context():
            job = Job(
                id=job_id,
                status="queued",
                match_mode="any",
                threshold=0.38,
                gallery_source=str(gallery_dir),
                created_at=utc_now(),
            )
            db.session.add(job)
            db.session.commit()

        job_runner.run_sorting_job(app, job_id)

        with app.app_context():
            job = db.session.get(Job, job_id)
            assert job.status == "completed"
            assert job.total_images == 1
            assert job.matched_count == 1

        assert (output_dir / "report.json").exists()
