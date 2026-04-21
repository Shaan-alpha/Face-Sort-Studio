"""
Face Sort Studio — Bootstrap
==============================
Downloads YuNet and SFace ONNX models from the OpenCV zoo
if they aren't already present in data/models/.
"""

import os
import urllib.request
import sys

MODEL_URLS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
}


def ensure_models_exist(models_dir: str) -> None:
    """Download any missing model files into *models_dir*."""
    os.makedirs(models_dir, exist_ok=True)

    for filename, url in MODEL_URLS.items():
        dest = os.path.join(models_dir, filename)
        if os.path.exists(dest):
            continue
        print(f"[bootstrap] Downloading {filename} …")
        try:
            urllib.request.urlretrieve(url, dest)
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"[bootstrap] Saved {filename} ({size_mb:.1f} MB)")
        except Exception as exc:
            print(
                f"[bootstrap] WARNING — could not download {filename}: {exc}",
                file=sys.stderr,
            )
            print(
                f"[bootstrap] Please manually download from:\n  {url}\n"
                f"  and place it in: {models_dir}",
                file=sys.stderr,
            )
