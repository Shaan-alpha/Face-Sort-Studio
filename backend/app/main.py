"""
Face Sort Studio — Main Flask Application
==========================================
Central entry point. Registers routes, initialises the database,
and serves both the UI and the REST API that the frontend calls.
"""

import os
import uuid
import json
import shutil
import threading

from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, Response, stream_with_context
)
from sqlalchemy.engine import make_url
from werkzeug.utils import secure_filename

from .config import Config
from .database import db, Job, JobResult, TargetFace, utc_now
from .bootstrap import ensure_models_exist
from .services.job_runner import run_sorting_job


def _ensure_runtime_paths(app: Flask) -> None:
    """Create runtime directories needed by uploads, outputs, models, and SQLite."""
    for path_key in ("JOBS_DIR", "OUTPUTS_DIR", "MODELS_DIR"):
        os.makedirs(app.config[path_key], exist_ok=True)

    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not database_uri:
        return

    db_url = make_url(database_uri)
    if db_url.drivername != "sqlite" or not db_url.database:
        return
    if db_url.database == ":memory:":
        return

    db_dir = os.path.dirname(db_url.database)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# ── Flask app factory ────────────────────────────────────────────
def create_app(config_overrides=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    _ensure_runtime_paths(app)

    # Initialise SQLAlchemy
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Make sure DL model files are present
    if not app.config.get("SKIP_MODEL_BOOTSTRAP", False):
        ensure_models_exist(app.config["MODELS_DIR"])

    # ── Page routes ──────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template(
            "index.html",
            public_share_mode=app.config.get("PUBLIC_SHARE_MODE", False),
        )

    # ── API: create a new sorting job ────────────────────────────
    @app.route("/api/jobs", methods=["POST"])
    def create_job():
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(app.config["JOBS_DIR"], job_id)
        ref_dir = os.path.join(job_dir, "references")
        gal_dir = os.path.join(job_dir, "gallery")
        os.makedirs(ref_dir, exist_ok=True)
        os.makedirs(gal_dir, exist_ok=True)

        # Save reference photos
        ref_files = request.files.getlist("references")
        if not ref_files or all(f.filename == "" for f in ref_files):
            return jsonify({"error": "At least one reference photo is required."}), 400

        for f in ref_files:
            if f and f.filename:
                fname = secure_filename(f.filename)
                f.save(os.path.join(ref_dir, fname))

        # Gallery source — either uploads or a local folder path
        gallery_path = request.form.get("gallery_path", "").strip()
        gallery_files = request.files.getlist("gallery")

        has_uploads = gallery_files and any(g.filename != "" for g in gallery_files)

        if app.config.get("PUBLIC_SHARE_MODE", False) and gallery_path:
            return jsonify({
                "error": (
                    "Local Folder mode is disabled while the app is shared "
                    "publicly. Upload gallery photos instead."
                )
            }), 400

        if not has_uploads and not gallery_path:
            if app.config.get("PUBLIC_SHARE_MODE", False):
                return jsonify({
                    "error": "Upload gallery images to run a shared job."
                }), 400
            return jsonify({"error": "Provide gallery images or a folder path."}), 400

        if has_uploads:
            for g in gallery_files:
                if g and g.filename:
                    gname = secure_filename(g.filename)
                    g.save(os.path.join(gal_dir, gname))
            gallery_source = gal_dir
        else:
            if not os.path.isdir(gallery_path):
                return jsonify({"error": f"Folder not found: {gallery_path}"}), 400
            gallery_source = gallery_path

        match_mode = request.form.get(
            "match_mode", app.config["DEFAULT_MATCH_MODE"]
        ).strip().lower()
        if match_mode not in {"any", "all"}:
            return jsonify({"error": "Match mode must be 'any' or 'all'."}), 400

        raw_threshold = request.form.get(
            "threshold", str(app.config["DEFAULT_THRESHOLD"])
        )
        try:
            threshold = float(raw_threshold)
        except (TypeError, ValueError):
            return jsonify({"error": "Threshold must be a number."}), 400

        if not 0.20 <= threshold <= 0.70:
            return jsonify({
                "error": "Threshold must be between 0.20 and 0.70."
            }), 400

        # Persist job record
        job = Job(
            id=job_id,
            status="queued",
            match_mode=match_mode,
            threshold=threshold,
            gallery_source=gallery_source,
            created_at=utc_now(),
        )
        db.session.add(job)
        db.session.commit()

        # Run in background thread so the request returns immediately
        thread = threading.Thread(
            target=run_sorting_job,
            args=(app, job_id),
            daemon=True,
        )
        thread.start()

        return jsonify({"job_id": job_id, "status": "queued"}), 202

    # ── API: job status (polled by frontend) ─────────────────────
    @app.route("/api/jobs/<job_id>")
    def job_status(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job.to_dict())

    # ── API: stream real-time progress via SSE ───────────────────
    @app.route("/api/jobs/<job_id>/stream")
    def job_stream(job_id):
        log_path = os.path.join(app.config["JOBS_DIR"], job_id, "progress.log")

        def generate():
            last_pos = 0
            while True:
                job = db.session.get(Job, job_id)
                if not job:
                    break
                if os.path.exists(log_path):
                    with open(log_path, "r") as fh:
                        fh.seek(last_pos)
                        new_lines = fh.read()
                        last_pos = fh.tell()
                    if new_lines:
                        for line in new_lines.strip().split("\n"):
                            yield f"data: {line}\n\n"
                if job.status in ("completed", "failed"):
                    yield f"data: {json.dumps({'status': job.status})}\n\n"
                    break
                import time
                time.sleep(0.5)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
        )

    # ── API: job history ─────────────────────────────────────────
    @app.route("/api/jobs")
    def list_jobs():
        jobs = Job.query.order_by(Job.created_at.desc()).limit(50).all()
        return jsonify([j.to_dict() for j in jobs])

    # ── API: delete a job ────────────────────────────────────────
    @app.route("/api/jobs/<job_id>", methods=["DELETE"])
    def delete_job(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        # Remove files
        job_dir = os.path.join(app.config["JOBS_DIR"], job_id)
        out_dir = os.path.join(app.config["OUTPUTS_DIR"], job_id)
        shutil.rmtree(job_dir, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)

        # Remove DB records
        JobResult.query.filter_by(job_id=job_id).delete()
        TargetFace.query.filter_by(job_id=job_id).delete()
        db.session.delete(job)
        db.session.commit()

        return jsonify({"deleted": job_id})

    # ── API: serve output files ──────────────────────────────────
    @app.route("/outputs/<path:filepath>")
    def serve_output(filepath):
        return send_from_directory(app.config["OUTPUTS_DIR"], filepath)

    # ── API: serve job report ────────────────────────────────────
    @app.route("/api/jobs/<job_id>/report")
    def job_report(job_id):
        report_path = os.path.join(
            app.config["OUTPUTS_DIR"], job_id, "report.json"
        )
        if not os.path.exists(report_path):
            return jsonify({"error": "Report not ready"}), 404
        with open(report_path) as fh:
            return jsonify(json.load(fh))

    # ── API: analytics summary for dashboard ─────────────────────
    @app.route("/api/analytics")
    def analytics():
        total_jobs = Job.query.count()
        completed = Job.query.filter_by(status="completed").count()
        total_photos = db.session.query(
            db.func.sum(Job.total_images)
        ).scalar() or 0
        total_matched = db.session.query(
            db.func.sum(Job.matched_count)
        ).scalar() or 0
        return jsonify({
            "total_jobs": total_jobs,
            "completed_jobs": completed,
            "total_photos_processed": total_photos,
            "total_matched": total_matched,
        })

    return app
