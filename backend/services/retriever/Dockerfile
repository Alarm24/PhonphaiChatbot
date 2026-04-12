# --- Builder Stage ---
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS builder

# 1. Grab the uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. Install Python 3.11 and build dependencies
# We don't need pip here because uv handles the installations
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Create a virtual environment using the system python3.11
RUN uv venv /opt/venv --python=python3.11
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 4. Copy and Install requirements using uv
# Notice how we pass the extra-index-url directly to uv pip install
COPY services/retriever/requirements.txt .
RUN uv pip install --no-cache \
    --index-strategy unsafe-best-match \
    --extra-index-url https://download.pytorch.org/whl/cu124 \
    -r requirements.txt

# 5. Copy and install shared protos
COPY protos /protos
RUN uv pip install --no-cache /protos


# --- Final Stage ---
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# 1. Install ONLY the bare Python 3.11 runtime (no compilers or dev tools)
RUN apt-get update && apt-get install -y \
    python3.11 \
    && rm -rf /var/lib/apt/lists/*

# Set up symbolic link for convenience
RUN ln -sf /usr/bin/python3.11 /usr/bin/python

WORKDIR /app

# 2. Copy the populated virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv

# 3. Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

# 4. Explicitly set HuggingFace Cache Directory
ENV HF_HOME=/root/.cache/huggingface

# 5. Define Build Arguments
ARG RERANK_MODEL_NAME="BAAI/bge-reranker-v2-m3"
ARG EMBEDDING_MODEL_NAME="intfloat/multilingual-e5-large"

# 6. Bake models directly into the image layer
RUN python -c "\
import sentence_transformers; \
from sentence_transformers import CrossEncoder; \
from langchain_huggingface import HuggingFaceEmbeddings; \
rerank_model = '${RERANK_MODEL_NAME}'; \
embed_model = '${EMBEDDING_MODEL_NAME}'; \
print(f'⏳ Loading Reranker Model: {rerank_model}...'); \
CrossEncoder(rerank_model); \
print(f'⏳ Loading Embedding Model: {embed_model}...'); \
HuggingFaceEmbeddings(model_name=embed_model); \
print('✅ Models successfully cached/baked!')"

# 7. Copy the actual application code
COPY services/retriever/ .

EXPOSE 50051
CMD ["python", "main.py"]