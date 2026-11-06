FROM python:3.12-slim

# Dependencias del sistema: fuentes para subtítulos y libsndfile para soundfile
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core libsndfile1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Hugging Face Spaces ejecuta el contenedor con el usuario UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/app/.venv/bin:$PATH \
    HOST=0.0.0.0 \
    PORT=7860 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy
WORKDIR /home/user/app

# Instalar dependencias de Python (capa cacheada)
COPY --chown=user pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project --no-dev

# Pre-descargar modelos de voz para que el arranque sea inmediato
RUN mkdir -p models projects outputs \
    && curl -fsSL -o models/kokoro-v1.0.int8.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx \
    && curl -fsSL -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin \
    && curl -fsSL -o models/es_MX-claude-high.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx \
    && curl -fsSL -o models/es_MX-claude-high.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/claude/high/es_MX-claude-high.onnx.json \
    && curl -fsSL -o models/es_MX-ald-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx \
    && curl -fsSL -o models/es_MX-ald-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json

# Código de la aplicación
COPY --chown=user app.py video_pipeline.py frutinovela.py ./
COPY --chown=user static ./static

EXPOSE 7860
CMD ["python", "app.py"]
