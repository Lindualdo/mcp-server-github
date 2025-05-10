from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
import subprocess
import os
import json

app = FastAPI()
message_queue = asyncio.Queue()

# Caminho do binário MCP compilado
BINARY_PATH = "/usr/local/bin/github-mcp-server"

# Inicia o processo do MCP Server
mcp_proc = subprocess.Popen(
    [BINARY_PATH, "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    env={**os.environ, "GITHUB_TOOLSETS": "all"}
)

# Leitura assíncrona do MCP stdout
async def read_stdout():
    while True:
        line = await asyncio.to_thread(mcp_proc.stdout.readline)
        if line:
            await message_queue.put(line.strip())

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(read_stdout())

@app.get("/sse")
async def sse(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(message_queue.get(), timeout=5)
                # Log de debug da resposta enviada ao cliente
                print(f"🧪 Enviando SSE: {message}")
                yield f"data: {message}\n\n"
            except asyncio.TimeoutError:
                continue
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/tool/run")
async def run_tool(request: Request):
    body = await request.json()
    tool = body.get("tool")
    args = body.get("args", {})

    if not tool:
        return JSONResponse(status_code=400, content={"error": "Missing tool name"})

    cmd = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": args
        }
    }

    try:
        mcp_proc.stdin.write(json.dumps(cmd) + "\n")
        mcp_proc.stdin.flush()
        return {"status": "sent"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
