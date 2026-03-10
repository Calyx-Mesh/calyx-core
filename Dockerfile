# INGRVM Hub: Production Environment
# Optimized for Neuromorphic Mesh Orchestration (Phase 7)

FROM python:3.12-slim

# --- Environment Configuration ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INGRVM_HOME=/app \
    INGRVM_HUB_HOST=0.0.0.0 \
    INGRVM_HUB_PORT=8000 \
    INGRVM_LOG_PATH=/app/data/logs/node_activity.jsonl

# --- Working Directory ---
WORKDIR $INGRVM_HOME

# --- System Dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# --- Python Dependencies ---
# Note: We use a specific hub-requirements set to avoid heavy CUDA/Torch 
# dependencies if running on a standard cloud CPU instance.
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn zeroconf python-dotenv psutil pydantic requests

# --- Application Setup ---
COPY . .

# Create persistent data directories for SQLite and Logs
RUN mkdir -p /app/data/logs /app/neuromorphic_env /app/ingrvms

# --- Mesh Connectivity ---
# API: 8000 | P2P: 60001 | Zeroconf: 5353
EXPOSE 8000 60001 5353/udp

# --- Launch Sequence ---
# Using the Hub Server as the entry point for orchestrators
CMD ["python", "hub_server.py"]

