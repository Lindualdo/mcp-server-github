from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
import subprocess
import os
import json

app = FastAPI()

BINARY_PATH = "/usr/local/bin/github-mcp-server"

mcp_proc = subprocess.Popen(
    [BINARY_PATH, "stdio"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    env={**os.environ, "GITHUB_TOOLSETS": "all"}
)

@app.get("/sse")
async def sse(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            line = mcp_proc.stdout.readline()
            if line:
                print(f"📡 MCP respondeu: {line.strip()}")
                yield f"data: {line.strip()}

"
            await asyncio.sleep(0.1)
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

    print(f"🚀 Enviando comando para MCP: {cmd}")
    try:
        mcp_proc.stdin.write(json.dumps(cmd) + "\n")
        mcp_proc.stdin.flush()
        return {"status": "sent"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
