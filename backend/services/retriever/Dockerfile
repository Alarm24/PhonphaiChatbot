FROM python:3.11-slim

WORKDIR /app

# Install system utilities needed for ChromaDB and Vector packages
RUN apt-get update && apt-get install -y gcc g++ python3-dev && rm -rf /var/lib/apt/lists/*

# 1. Copy and install the Retriever specific requirements
COPY services/retriever/requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# 2. Copy and install the shared protos package
COPY protos /protos
RUN pip install /protos

# 3. Explicitly set HuggingFace Cache Directory
ENV HF_HOME=/root/.cache/huggingface

# 4. Define Build Arguments (with fallbacks just in case)
ARG RERANK_MODEL_NAME="BAAI/bge-reranker-v2-m3"
ARG EMBEDDING_MODEL_NAME="intfloat/multilingual-e5-large"

# 5. Bake models into the image using the variables
RUN python -c "\
from sentence_transformers import CrossEncoder; \
from langchain_huggingface import HuggingFaceEmbeddings; \
rerank_model = '${RERANK_MODEL_NAME}'; \
embed_model = '${EMBEDDING_MODEL_NAME}'; \
print(f'⏳ Downloading Reranker Model: {rerank_model}...'); \
CrossEncoder(rerank_model); \
print(f'⏳ Downloading Embedding Model: {embed_model}...'); \
HuggingFaceEmbeddings(model_name=embed_model); \
print('✅ All models successfully baked into image!')"

# 6. Copy the actual Retriever application code
COPY services/retriever/ .

EXPOSE 50051

CMD ["python", "main.py"]