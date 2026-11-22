FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY orchestrator/requirements.txt ./orchestrator/requirements.txt
COPY mcp-server/requirements.txt ./mcp-server/requirements.txt

RUN pip install --no-cache-dir -r orchestrator/requirements.txt -r mcp-server/requirements.txt

# Copy source code
COPY orchestrator/ ./orchestrator/
COPY mcp-server/ ./mcp-server/

ENV PYTHONUNBUFFERED=1
ENV ORCHESTRATOR_PORT=8888

EXPOSE 8888

CMD ["python", "orchestrator/app.py"]
