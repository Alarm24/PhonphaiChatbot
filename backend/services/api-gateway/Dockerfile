FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# 1. Copy and install the API Gateway specific requirements
# (Path is relative to the root backend/ folder due to compose build context)
COPY services/api-gateway/requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# 2. Copy and install the shared protos package
COPY protos /protos
RUN pip install /protos

# 3. Copy the actual API Gateway application code
COPY services/api-gateway/ .

# Expose FastAPI default port
EXPOSE 8000

# Run the API Gateway
CMD ["python", "main.py"]