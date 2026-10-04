# Hugging Face Spaces — Docker SDK image for the Flask / Design.md web app.
FROM python:3.11-slim

# Build tools some wheels occasionally need.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# HF Spaces runs the container as uid 1000; set up a matching user.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PORT=7860 \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# Install dependencies. Use the CPU-only torch wheel to keep the image small.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt \
 && python -m spacy download en_core_web_sm

# Pre-download model weights so the first request is fast (no runtime download).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
 && python -c "from transformers import T5ForConditionalGeneration, T5TokenizerFast; T5TokenizerFast.from_pretrained('t5-small'); T5ForConditionalGeneration.from_pretrained('t5-small')"

# App code + data.
COPY --chown=user . .

EXPOSE 7860
CMD ["python", "server.py"]
