FROM python:3.13-slim

WORKDIR /app

# Install system dependencies required for OpenCV (used by imutils)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy source code
COPY thsr_ticket ./thsr_ticket
COPY web ./web

# Expose port
EXPOSE 8000

# Run the server
# using uvicorn directly via uv run
CMD ["uv", "run", "uvicorn", "thsr_ticket.server:app", "--host", "0.0.0.0", "--port", "8000"]
