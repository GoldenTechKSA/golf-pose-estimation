# SwingLens ML backend — serves both the API (uvicorn) and the Celery
# worker; docker-compose picks the command per service.
FROM python:3.12-slim

# ffmpeg: video normalization/transcode. libgl/libglib: OpenCV runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Non-root runtime user; /data holds uploads, outputs, and model weights.
RUN useradd --create-home swinglens \
    && mkdir -p /data/storage /data/models \
    && chown -R swinglens:swinglens /data /app
USER swinglens

# Ultralytics downloads pose weights into the working directory on first
# use — run from the models volume so weights persist across restarts.
WORKDIR /data/models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
