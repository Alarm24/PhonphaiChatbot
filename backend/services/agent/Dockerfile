FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# 1. Copy and install the service's specific requirements
COPY services/agent/requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# 2. COPY AND INSTALL THE SHARED PROTOS PACKAGE
COPY protos /protos
RUN pip install /protos

# 3. Copy the actual application code
COPY services/agent/ .

EXPOSE 50052
CMD ["python", "main.py"]