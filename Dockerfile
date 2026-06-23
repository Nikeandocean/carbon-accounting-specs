FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml README.md ./
COPY mcp_server/ mcp_server/
COPY specs/ specs/
COPY schemas/ schemas/

RUN pip install --no-cache-dir .

# Default: stdio mode (for local use)
# Override with MCP_TRANSPORT=streamable-http for HTTP mode
ENV MCP_TRANSPORT=stdio
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "mcp_server"]
