FROM golang:1.23.8-bookworm AS builder


WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y git && \
    go mod tidy && \
    go build -o github-mcp-server ./cmd/github-mcp-server

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/github-mcp-server /usr/local/bin/github-mcp-server
COPY mcp_sse_proxy.py ./mcp_sse_proxy.py

RUN pip install --no-cache-dir fastapi uvicorn

EXPOSE 3000

ENV GITHUB_PERSONAL_ACCESS_TOKEN=changeme

CMD ["uvicorn", "mcp_sse_proxy:app", "--host", "0.0.0.0", "--port", "3000"]
