FROM python:3.11-slim

WORKDIR /app

# Install system utilities needed for ChromaDB and Vector packages
RUN apt-get update && apt-get install -y gcc g++ python3-dev && rm -rf /var/lib/apt/lists/*

# 1. Copy and install the Retriever specific requirements
# (Path is relative to the root backend/ folder due to compose build context)
COPY services/retriever/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy and install the shared protos package
COPY protos /protos
RUN pip install /protos

# 3. Copy the actual Retriever application code
COPY services/retriever/ .

# Expose the gRPC port for the Retriever
EXPOSE 50051

# Run the Retriever Service
CMD ["python", "main.py"]