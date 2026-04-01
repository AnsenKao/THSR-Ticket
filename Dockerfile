FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (OpenCV + Xvfb for headless Playwright)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Install Playwright Chromium browser and its system dependencies
RUN uv run playwright install chromium --with-deps

# Copy source code
COPY thsr_ticket ./thsr_ticket
COPY web ./web

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8000

ENV DISPLAY=:99

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "thsr_ticket.server:app", "--host", "0.0.0.0", "--port", "8000"]
