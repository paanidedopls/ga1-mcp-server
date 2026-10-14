from __future__ import annotations

import hashlib
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

EMAIL = "24f2001785@ds.study.iitm.ac.in".strip().lower()
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
}

app = FastAPI(title="GA1 Challenge MCP Server", docs_url="/docs", redoc_url=None)

# Useful if the endpoint is tested from a browser-based MCP client.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "*",
        "MCP-Protocol-Version",
        "MCP-Session-Id",
        "X-Exam-Challenge",
        "X-Exam-Timestamp",
        "X-Exam-Signature",
    ],
    expose_headers=["MCP-Protocol-Version"],
)


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def protocol_response(payload: dict[str, Any], version: str | None = None) -> JSONResponse:
    headers = {}
    if version:
        headers["MCP-Protocol-Version"] = version
    return JSONResponse(payload, headers=headers)


@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ga1-challenge-mcp", "endpoint": "/mcp"}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        message = await request.json()
    except Exception:
        return JSONResponse({"error": "Request body must be valid JSON"}, status_code=400)

    if not isinstance(message, dict):
        return JSONResponse({"error": "Expected one JSON-RPC object"}, status_code=400)

    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    # MCP notifications have no id and are acknowledged with HTTP 202 and no body.
    if method == "notifications/initialized" and "id" not in message:
        return Response(status_code=202)

    if method == "initialize":
        requested_version = params.get("protocolVersion") if isinstance(params, dict) else None
        version = requested_version if requested_version in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        result = {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "ga1-challenge-mcp", "version": "1.0.0"},
        }
        return protocol_response({"jsonrpc": "2.0", "id": request_id, "result": result}, version)

    if method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "solve_challenge",
                    "description": "Return the required short SHA-256 digest for this request's X-Exam-Challenge header.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                }
            ]
        }
        version = request.headers.get("MCP-Protocol-Version") or DEFAULT_PROTOCOL_VERSION
        return protocol_response({"jsonrpc": "2.0", "id": request_id, "result": result}, version)

    if method == "tools/call":
        tool_name = params.get("name") if isinstance(params, dict) else None
        if tool_name != "solve_challenge":
            return protocol_response(rpc_error(request_id, -32602, "Unknown tool"))

        # Intentionally read challenge from HTTP headers, never from tool arguments/body.
        challenge = request.headers.get("X-Exam-Challenge")
        if challenge is None:
            return protocol_response(rpc_error(request_id, -32603, "Missing X-Exam-Challenge request header"))

        digest = hashlib.sha256(f"{challenge}:{EMAIL}".encode("utf-8")).hexdigest()[:16]
        result = {"content": [{"type": "text", "text": digest}], "isError": False}
        version = request.headers.get("MCP-Protocol-Version") or DEFAULT_PROTOCOL_VERSION
        return protocol_response({"jsonrpc": "2.0", "id": request_id, "result": result}, version)

    if isinstance(method, str) and method.startswith("notifications/") and "id" not in message:
        return Response(status_code=202)

    if "id" in message:
        return protocol_response(rpc_error(request_id, -32601, f"Method not found: {method}"))
    return Response(status_code=202)


@app.get("/mcp")
async def mcp_get_not_supported():
    # This server doesn't initiate server-to-client notifications or SSE streams.
    return Response(status_code=405, headers={"Allow": "POST"})
