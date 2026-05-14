from setuptools import setup, find_packages
import os

with open("VERSION", "r") as f:
    version = f.read().strip()

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="face-sort-studio",
    version=version,
    author="Shaan-alpha",
    description="Local deep-learning photo sorting — powered by face recognition.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Shaan-alpha/Face-Sort-Studio",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask>=2.0.0",
        "flask-sqlalchemy",
        "opencv-python-headless",
        "numpy",
        "pillow",
        "click",
        "pystray",
        "python-multipart",
        "werkzeug",
        "sqlalchemy",
    ],
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
    python_requires=">=3.8",
)
