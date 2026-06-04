from setuptools import setup, find_packages
import os

with open("VERSION", "r") as f:
    version = f.read().strip()

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Single source of truth for dependencies — keep requirements.txt and the
# installed package in lockstep so `pip install .` and `pip install -r
# requirements.txt` resolve the same, tested dependency set.
with open("requirements.txt", "r", encoding="utf-8") as f:
    install_requires = []
    for line in f:
        # Strip inline comments (pip allows them; PEP 508 specifiers do not).
        spec = line.split("#", 1)[0].strip()
        if spec:
            install_requires.append(spec)

setup(
    name="face-sort-studio",
    version=version,
    author="Shaan-alpha",
    description="Privacy-first local photo organization powered by deep learning face recognition.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Shaan-alpha/face-sort-studio",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "face-sort=face_sort.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
