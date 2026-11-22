FROM python:3.11-slim

WORKDIR /app

COPY mcp-server/requirements.txt ./mcp-server/requirements.txt
RUN pip install --no-cache-dir -r mcp-server/requirements.txt

COPY mcp-server/ ./mcp-server/

ENV PYTHONUNBUFFERED=1
ENV INFRAGPT_K8S_MODE=mock
ENV MCP_TRANSPORT=http
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8000

EXPOSE 8000

CMD ["python", "mcp-server/server.py"]
