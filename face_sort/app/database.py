"""
Face Sort Studio — Database Models
====================================
SQLAlchemy models for Jobs, Results, and Target Faces.
Uses SQLite locally; swap the URI in config.py for Azure SQL / PostgreSQL.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utc_now() -> datetime:
    """Return a naive UTC timestamp for SQLite/SQLAlchemy DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Job(db.Model):
    """One sorting run submitted by the user."""

    __tablename__ = "jobs"

    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(
        db.String(20), nullable=False, default="queued"
    )  # queued | processing | completed | failed
    match_mode = db.Column(db.String(10), nullable=False, default="any")
    threshold = db.Column(db.Float, nullable=False, default=0.38)
    gallery_source = db.Column(db.Text, nullable=True)

    total_images = db.Column(db.Integer, default=0)
    matched_count = db.Column(db.Integer, default=0)
    partial_count = db.Column(db.Integer, default=0)
    unmatched_count = db.Column(db.Integer, default=0)
    targets_found = db.Column(db.Integer, default=0)

    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)

    results = db.relationship("JobResult", backref="job", lazy=True)
    targets = db.relationship("TargetFace", backref="job", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "match_mode": self.match_mode,
            "threshold": self.threshold,
            "gallery_source": self.gallery_source,
            "total_images": self.total_images,
            "matched_count": self.matched_count,
            "partial_count": self.partial_count,
            "unmatched_count": self.unmatched_count,
            "targets_found": self.targets_found,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class JobResult(db.Model):
    """Per-image result within a job."""

    __tablename__ = "job_results"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(
        db.String(36), db.ForeignKey("jobs.id"), nullable=False
    )
    filename = db.Column(db.String(260), nullable=False)
    category = db.Column(
        db.String(20), nullable=False
    )  # matched | partial | unmatched
    faces_detected = db.Column(db.Integer, default=0)
    matched_targets = db.Column(db.Text, nullable=True)  # JSON list
    confidence_scores = db.Column(db.Text, nullable=True)  # JSON list


class TargetFace(db.Model):
    """A discovered target person from reference photos."""

    __tablename__ = "target_faces"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(
        db.String(36), db.ForeignKey("jobs.id"), nullable=False
    )
    person_label = db.Column(db.String(100), nullable=False)
    source_file = db.Column(db.String(260), nullable=True)
    embedding_hash = db.Column(db.String(64), nullable=True)
