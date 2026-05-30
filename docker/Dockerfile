# Linux + Python 3.11 + Essentia, for verifying / running the high-accuracy
# analysis backend without a Windows-native Essentia build.
#
# Build & run the backend self-test (from the repo root):
#   docker build -f docker/Dockerfile -t wavemash-essentia .
#   docker run --rm wavemash-essentia
#
# Expected: backends shows essentia=True, and BPM/key/downbeats are printed.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# essentia (manylinux wheel) + the analysis dependencies.
RUN pip install --no-cache-dir \
        essentia numpy scipy soundfile librosa audioflux

# Only the analysis module is needed for the backend self-test (no Qt).
COPY desktop_app/__init__.py /app/desktop_app/__init__.py
COPY desktop_app/analysis.py /app/desktop_app/analysis.py
COPY docker/verify_essentia.py /app/verify_essentia.py

CMD ["python", "verify_essentia.py"]
