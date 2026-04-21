"""
Face Sort Studio — Job Runner
================================
Orchestrates an end-to-end sorting job:

1.  Load reference photos → detect faces → build target embeddings
2.  Cluster targets into distinct persons
3.  Scan each gallery image
4.  Compare gallery faces against all target persons
5.  Copy images into matched / partial / unmatched / by_target
6.  Write report.json
7.  Update the database
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict

import cv2
import numpy as np

from ..config import Config
from ..database import db, Job, JobResult, TargetFace, utc_now
from .face_engine import FaceEngine


# ── Helpers ──────────────────────────────────────────────────────
def _log(job_dir: str, message: str):
    """Append a line to the job's progress log (consumed by SSE stream)."""
    log_path = os.path.join(job_dir, "progress.log")
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"msg": message}) + "\n")


def _is_image(path: str, allowed_extensions) -> bool:
    return Path(path).suffix.lower() in allowed_extensions


def _emb_hash(emb: np.ndarray) -> str:
    return hashlib.sha256(emb.tobytes()).hexdigest()[:16]


# ── Main entry point — called from background thread ─────────────
def run_sorting_job(app, job_id: str):
    """Execute the complete sorting pipeline inside an app context."""
    with app.app_context():
        job = db.session.get(Job, job_id)
        if not job:
            return

        allowed_extensions = app.config.get(
            "ALLOWED_EXTENSIONS", Config.ALLOWED_EXTENSIONS
        )
        jobs_dir = app.config["JOBS_DIR"]
        outputs_dir = app.config["OUTPUTS_DIR"]
        models_dir = app.config["MODELS_DIR"]

        job_dir = os.path.join(jobs_dir, job_id)
        out_dir = os.path.join(outputs_dir, job_id)
        os.makedirs(out_dir, exist_ok=True)

        try:
            job.status = "processing"
            db.session.commit()
            _log(job_dir, "Initialising face engine …")

            engine = FaceEngine(models_dir)

            # ── Step 1: process reference photos ─────────────────
            ref_dir = os.path.join(job_dir, "references")
            ref_embeddings = []  # list of (filename, embedding)

            ref_files = [
                f
                for f in os.listdir(ref_dir)
                if _is_image(f, allowed_extensions)
            ]
            _log(job_dir, f"Found {len(ref_files)} reference photo(s)")

            for fname in ref_files:
                fpath = os.path.join(ref_dir, fname)
                results = engine.process_image(fpath)
                for _, emb in results:
                    ref_embeddings.append((fname, emb))
                _log(
                    job_dir,
                    f"  {fname}: {len(results)} face(s) detected",
                )

            if not ref_embeddings:
                raise RuntimeError(
                    "No faces detected in any reference photo. "
                    "Try clearer, front-facing images."
                )

            # ── Step 2: cluster into distinct persons ────────────
            groups = engine.cluster_targets(
                ref_embeddings, threshold=job.threshold
            )
            persons: List[Dict] = []
            targets_dir = os.path.join(out_dir, "targets")
            os.makedirs(targets_dir, exist_ok=True)

            for idx, group in enumerate(groups):
                label = f"Person_{idx + 1:02d}"
                rep_emb = group[0][1]  # representative embedding
                persons.append({
                    "label": label,
                    "embedding": rep_emb,
                    "source_files": [g[0] for g in group],
                })

                # Save a cropped reference face for the report
                src_file = group[0][0]
                src_path = os.path.join(ref_dir, src_file)
                img = cv2.imread(src_path)
                if img is not None:
                    faces = engine.detect_faces(img)
                    if len(faces) > 0:
                        x, y, w, h = (
                            int(faces[0][0]),
                            int(faces[0][1]),
                            int(faces[0][2]),
                            int(faces[0][3]),
                        )
                        # Add margin
                        margin = int(max(w, h) * 0.2)
                        y1 = max(0, y - margin)
                        y2 = min(img.shape[0], y + h + margin)
                        x1 = max(0, x - margin)
                        x2 = min(img.shape[1], x + w + margin)
                        crop = img[y1:y2, x1:x2]
                        cv2.imwrite(
                            os.path.join(targets_dir, f"{label}.jpg"), crop
                        )

                # Persist to DB
                tf = TargetFace(
                    job_id=job_id,
                    person_label=label,
                    source_file=group[0][0],
                    embedding_hash=_emb_hash(rep_emb),
                )
                db.session.add(tf)

            job.targets_found = len(persons)
            db.session.commit()
            _log(
                job_dir,
                f"Discovered {len(persons)} target person(s)",
            )

            # ── Step 3: scan gallery ─────────────────────────────
            gallery_source = job.gallery_source
            gallery_files = sorted(
                f
                for f in os.listdir(gallery_source)
                if _is_image(f, allowed_extensions)
            )
            total = len(gallery_files)
            job.total_images = total
            db.session.commit()
            _log(job_dir, f"Scanning {total} gallery image(s) …")

            # Prepare output folders
            matched_dir = os.path.join(out_dir, "matched")
            partial_dir = os.path.join(out_dir, "partial")
            unmatched_dir = os.path.join(out_dir, "unmatched")
            os.makedirs(matched_dir, exist_ok=True)
            os.makedirs(partial_dir, exist_ok=True)
            os.makedirs(unmatched_dir, exist_ok=True)

            by_target_dirs = {}
            for p in persons:
                d = os.path.join(out_dir, "by_target", p["label"])
                os.makedirs(d, exist_ok=True)
                by_target_dirs[p["label"]] = d

            matched_count = 0
            partial_count = 0
            unmatched_count = 0
            results_for_report = []

            for i, fname in enumerate(gallery_files):
                fpath = os.path.join(gallery_source, fname)
                detections = engine.process_image(fpath)

                matched_persons = set()
                best_scores: Dict[str, float] = {}

                for _, gal_emb in detections:
                    for p in persons:
                        score = engine.compare(gal_emb, p["embedding"])
                        if score >= job.threshold:
                            matched_persons.add(p["label"])
                            if (
                                p["label"] not in best_scores
                                or score > best_scores[p["label"]]
                            ):
                                best_scores[p["label"]] = score

                matched_labels = sorted(matched_persons)

                # Determine category
                if job.match_mode == "all":
                    all_labels = {p["label"] for p in persons}
                    if matched_persons == all_labels:
                        category = "matched"
                    elif matched_persons:
                        category = "partial"
                    else:
                        category = "unmatched"
                else:  # "any"
                    if matched_persons:
                        category = "matched"
                    else:
                        category = "unmatched"

                # Copy file to the right folder
                if category == "matched":
                    shutil.copy2(fpath, os.path.join(matched_dir, fname))
                    matched_count += 1
                elif category == "partial":
                    shutil.copy2(fpath, os.path.join(partial_dir, fname))
                    partial_count += 1
                else:
                    shutil.copy2(fpath, os.path.join(unmatched_dir, fname))
                    unmatched_count += 1

                # Copy into by_target folders
                for person_label in matched_labels:
                    target_dir = by_target_dirs[person_label]
                    shutil.copy2(fpath, os.path.join(target_dir, fname))

                # DB record
                jr = JobResult(
                    job_id=job_id,
                    filename=fname,
                    category=category,
                    faces_detected=len(detections),
                    matched_targets=json.dumps(matched_labels),
                    confidence_scores=json.dumps(best_scores),
                )
                db.session.add(jr)

                results_for_report.append({
                    "filename": fname,
                    "category": category,
                    "faces_detected": len(detections),
                    "matched_targets": matched_labels,
                    "scores": best_scores,
                })

                # Progress update every image
                pct = int((i + 1) / total * 100)
                _log(
                    job_dir,
                    f"[{pct}%] {fname} → {category}"
                    + (
                        f" ({', '.join(matched_labels)})"
                        if matched_labels
                        else ""
                    ),
                )

            # ── Step 4: finalise ─────────────────────────────────
            job.matched_count = matched_count
            job.partial_count = partial_count
            job.unmatched_count = unmatched_count
            job.status = "completed"
            job.completed_at = utc_now()
            db.session.commit()

            # Write report.json
            report = {
                "job_id": job_id,
                "match_mode": job.match_mode,
                "threshold": job.threshold,
                "total_images": total,
                "matched": matched_count,
                "partial": partial_count,
                "unmatched": unmatched_count,
                "targets": [
                    {
                        "label": p["label"],
                        "source_files": p["source_files"],
                    }
                    for p in persons
                ],
                "results": results_for_report,
            }
            with open(
                os.path.join(out_dir, "report.json"), "w", encoding="utf-8"
            ) as fh:
                json.dump(report, fh, indent=2)

            _log(job_dir, f"✓ Done — {matched_count} matched, "
                 f"{partial_count} partial, {unmatched_count} unmatched")

        except Exception as exc:
            db.session.rollback()
            job = db.session.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = utc_now()
                db.session.commit()
            _log(job_dir, f"✗ Error: {exc}")
