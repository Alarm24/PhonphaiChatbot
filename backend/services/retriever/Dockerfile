FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# 1. Install Python 3.11 and necessary tools
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up symbolic links so "python" and "pip" always use 3.11
RUN ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# 3. Upgrade pip using the module approach
RUN python -m pip install --upgrade pip

# 4. Copy and Install requirements
COPY services/retriever/requirements.txt .
RUN python -m pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cu124 \
    -r requirements.txt

# 5. Copy and install shared protos
COPY protos /protos
RUN python -m pip install /protos

# 6. Explicitly set HuggingFace Cache Directory
ENV HF_HOME=/root/.cache/huggingface

# 7. Define Build Arguments
ARG RERANK_MODEL_NAME="BAAI/bge-reranker-v2-m3"
ARG EMBEDDING_MODEL_NAME="intfloat/multilingual-e5-large"

# 8. Bake models - Use the same python executable
RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "\
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

COPY services/retriever/ .

EXPOSE 50051
CMD ["python", "main.py"]