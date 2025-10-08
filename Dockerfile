FROM node:18-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python
RUN pip3 install uv

# Copy Python app
COPY . .

# Install Python dependencies
RUN uv sync --frozen

# Install Evolution API
RUN npm install -g @evolution-api/evolution-api

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Evolution API in background\n\
evolution-api &\n\
\n\
# Wait for Evolution API to start\n\
sleep 10\n\
\n\
# Start Python bot\n\
cd /app && uv run python -m app.main\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 8000 8080

# Run startup script
CMD ["/app/start.sh"]