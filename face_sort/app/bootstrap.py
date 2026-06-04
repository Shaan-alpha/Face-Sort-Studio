"""
Face Sort Studio — Bootstrap
==============================
Downloads YuNet and SFace ONNX models from the OpenCV zoo
if they aren't already present in data/models/.

Downloads are written to a temporary ``*.part`` file and only renamed into
place once they pass a minimum-size check, so an interrupted download can
never leave a truncated file that later fails to load.
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

# Minimum expected sizes (bytes) — used to detect truncated/partial files.
# Actual sizes: YuNet ~0.23 MB, SFace ~36.9 MB. Floors are set well below
# the real sizes so a complete file always passes but a truncated one fails.
MODEL_MIN_BYTES = {
    "face_detection_yunet_2023mar.onnx": 150_000,
    "face_recognition_sface_2021dec.onnx": 30_000_000,
}


def _is_complete(path: str, filename: str) -> bool:
    """A model file is considered complete only if it meets its size floor."""
    if not os.path.exists(path):
        return False
    min_bytes = MODEL_MIN_BYTES.get(filename, 1)
    return os.path.getsize(path) >= min_bytes


def ensure_models_exist(models_dir: str) -> None:
    """Download any missing or incomplete model files into *models_dir*."""
    os.makedirs(models_dir, exist_ok=True)

    for filename, url in MODEL_URLS.items():
        dest = os.path.join(models_dir, filename)

        if _is_complete(dest, filename):
            continue

        # Remove a stale/truncated file left by a previous interrupted run.
        if os.path.exists(dest):
            print(
                f"[bootstrap] {filename} looks incomplete — re-downloading …",
                file=sys.stderr,
            )
            try:
                os.remove(dest)
            except OSError:
                pass

        tmp = dest + ".part"
        print(f"[bootstrap] Downloading {filename} …")
        try:
            urllib.request.urlretrieve(url, tmp)
            if not _is_complete(tmp, filename):
                raise IOError(
                    f"downloaded file is smaller than expected "
                    f"({os.path.getsize(tmp)} bytes)"
                )
            os.replace(tmp, dest)  # atomic rename — only a complete file lands
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"[bootstrap] Saved {filename} ({size_mb:.1f} MB)")
        except Exception as exc:
            # Clean up the partial download so the next run retries cleanly.
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            print(
                f"[bootstrap] WARNING — could not download {filename}: {exc}",
                file=sys.stderr,
            )
            print(
                f"[bootstrap] Please manually download from:\n  {url}\n"
                f"  and place it in: {models_dir}",
                file=sys.stderr,
            )
