# --- Builder Stage ---
FROM python:3.11-slim AS builder

# Grab the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system utilities needed for building wheels
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a virtual environment for uv to populate
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 1. Copy and install the API Gateway specific requirements
COPY services/api-gateway/requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# 2. Copy and install the shared protos package
COPY protos /protos
RUN uv pip install --no-cache /protos


# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

# 1. Copy ONLY the populated virtual environment from the builder stage
# This completely leaves behind uv, gcc, and intermediate build cache
COPY --from=builder /opt/venv /opt/venv

# 2. Activate the virtual environment in the final image
ENV PATH="/opt/venv/bin:$PATH"

# 3. Copy the actual API Gateway application code
COPY services/api-gateway/ .

# Expose FastAPI default port
EXPOSE 8000

# Run the API Gateway
CMD ["python", "main.py"]