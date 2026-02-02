FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# All environment variables in one layer
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    AWS_REGION=us-east-1 \
    AWS_DEFAULT_REGION=us-east-1

# Install system dependencies for OCR and PDF handling
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

# Install all requirements including the OTEL distro
RUN uv pip install -r requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 bedrock_agentcore

# Copy entire project
COPY . .

# Ensure the non-root user owns the files
RUN chown -R bedrock_agentcore:bedrock_agentcore /app
USER bedrock_agentcore

EXPOSE 9000
EXPOSE 8000
EXPOSE 8080

# Use your original OTEL entrypoint
CMD ["opentelemetry-instrument", "python", "-m", "core.agent"]