# --- Builder Stage ---
FROM python:3.11-slim AS builder

# 1. Grab the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. Install build dependencies (gcc is usually only needed for building wheels)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Create a virtual environment
RUN uv venv /opt/venv
# Ensure subsequent uv commands use this venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 4. Copy and install the service's specific requirements
COPY services/agent/requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# 5. Copy and install the shared protos package
COPY protos /protos
RUN uv pip install --no-cache /protos


# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

# 1. Copy ONLY the virtual environment from the builder stage
# This leaves uv, gcc, and build artifacts behind.
COPY --from=builder /opt/venv /opt/venv

# 2. Activate the virtual environment in the final image
ENV PATH="/opt/venv/bin:$PATH"

# 3. Copy the actual application code
COPY services/agent/ .

EXPOSE 50052
CMD ["python", "main.py"]