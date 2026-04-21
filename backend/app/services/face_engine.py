"""
Face Sort Studio — Face Engine
================================
Wraps OpenCV's YuNet (face detection) and SFace (face recognition)
into a clean API used by the job runner.

Architecture
------------
1.  detect_faces(image)       → list of bounding boxes + landmarks
2.  extract_embedding(image, face) → 128-d normalised vector
3.  compare(emb_a, emb_b)    → cosine similarity score  (0 … 1)
4.  cluster_targets(embeddings, threshold) → grouped person IDs

The engine is stateless — instantiate once, reuse across jobs.
"""

import os
import cv2
import numpy as np
from typing import List, Tuple, Optional


class FaceEngine:
    """High-level wrapper around YuNet + SFace ONNX models."""

    def __init__(
        self,
        models_dir: str,
        yunet_model: str = "face_detection_yunet_2023mar.onnx",
        sface_model: str = "face_recognition_sface_2021dec.onnx",
        score_threshold: float = 0.9,
        nms_threshold: float = 0.3,
        input_size: Tuple[int, int] = (300, 300),
    ):
        yunet_path = os.path.join(models_dir, yunet_model)
        sface_path = os.path.join(models_dir, sface_model)

        if not os.path.exists(yunet_path):
            raise FileNotFoundError(f"YuNet model not found: {yunet_path}")
        if not os.path.exists(sface_path):
            raise FileNotFoundError(f"SFace model not found: {sface_path}")

        self._detector = cv2.FaceDetectorYN.create(
            yunet_path,
            "",
            input_size,
            score_threshold,
            nms_threshold,
        )
        self._recognizer = cv2.FaceRecognizerSF.create(sface_path, "")
        self._input_size = input_size

    # ── Detection ────────────────────────────────────────────────
    def detect_faces(self, image: np.ndarray) -> np.ndarray:
        """Return an Nx15 array of detected faces (or empty array)."""
        h, w = image.shape[:2]
        self._detector.setInputSize((w, h))
        _, faces = self._detector.detect(image)
        return faces if faces is not None else np.array([])

    # ── Embedding ────────────────────────────────────────────────
    def extract_embedding(
        self, image: np.ndarray, face: np.ndarray
    ) -> np.ndarray:
        """Align the face and return a 128-d normalised embedding."""
        aligned = self._recognizer.alignCrop(image, face)
        embedding = self._recognizer.feature(aligned)
        return embedding.flatten()

    # ── Comparison ───────────────────────────────────────────────
    def compare(
        self,
        emb_a: np.ndarray,
        emb_b: np.ndarray,
        method: int = cv2.FaceRecognizerSF_FR_COSINE,
    ) -> float:
        """Cosine similarity between two embeddings (0 = different, 1 = same)."""
        score = self._recognizer.match(
            emb_a.reshape(1, -1),
            emb_b.reshape(1, -1),
            method,
        )
        return float(score)

    # ── Clustering reference faces into persons ──────────────────
    def cluster_targets(
        self,
        embeddings: List[Tuple[str, np.ndarray]],
        threshold: float = 0.38,
    ) -> List[List[Tuple[str, np.ndarray]]]:
        """
        Group reference face embeddings into distinct persons.

        Parameters
        ----------
        embeddings : list of (source_filename, embedding) tuples
        threshold  : cosine similarity above which two faces are
                     considered the same person

        Returns
        -------
        list of groups — each group is a list of (filename, embedding) tuples
        """
        groups: List[List[Tuple[str, np.ndarray]]] = []

        for item in embeddings:
            _, emb = item
            placed = False
            for group in groups:
                rep_emb = group[0][1]
                if self.compare(emb, rep_emb) >= threshold:
                    group.append(item)
                    placed = True
                    break
            if not placed:
                groups.append([item])

        return groups

    # ── Convenience: load + detect + embed in one call ───────────
    def process_image(
        self, image_path: str
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Read an image file and return a list of (face_box, embedding) tuples.
        Returns an empty list when no faces are found.
        """
        image = cv2.imread(image_path)
        if image is None:
            return []

        faces = self.detect_faces(image)
        results = []
        for face in faces:
            emb = self.extract_embedding(image, face)
            results.append((face, emb))
        return results

    # ── Draw detections (useful for debugging / preview) ─────────
    @staticmethod
    def draw_faces(
        image: np.ndarray,
        faces: np.ndarray,
        labels: Optional[List[str]] = None,
    ) -> np.ndarray:
        """Draw bounding boxes and optional labels on a copy of the image."""
        canvas = image.copy()
        for idx, face in enumerate(faces):
            x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if labels and idx < len(labels):
                cv2.putText(
                    canvas,
                    labels[idx],
                    (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
        return canvas
