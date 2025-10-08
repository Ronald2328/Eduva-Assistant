FROM node:18-slim

WORKDIR /app

# Install system dependencies including Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for Python
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install uv in virtual environment
RUN pip install uv

# Install Evolution API globally
RUN npm install -g @evolution-api/evolution-api

# Copy Python app
COPY . .

# Install Python dependencies
RUN uv sync --frozen

# Create supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose both ports
EXPOSE 8000 8080

# Start with supervisor (manages both processes)
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]