# Flask app — lightweight Docker image for cloud deployment.
FROM python:3.11-slim

# Build tools some wheels occasionally need.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PORT=5000 \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      "torch>=2.2" \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn \
 && python -m spacy download en_core_web_sm

# App code + data (no model pre-download — models load lazily on first request).
COPY --chown=user . .

EXPOSE 5000
CMD ["sh", "-c", "gunicorn server:app --bind 0.0.0.0:${PORT:-5000} --timeout 180 --workers 1"]
