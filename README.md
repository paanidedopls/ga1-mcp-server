# GA1 Challenge MCP Server

A small stateless MCP Streamable HTTP endpoint for the GA1 `solve_challenge` task.

## Local run

```bash
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The public MCP endpoint path is `/mcp`. The root path `/` is a simple health check.

## Deploy on Render

Create a **Web Service** from this repository and configure:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Submit `https://YOUR-SERVICE.onrender.com/mcp` to the grader.

## Behavior

- Handles `initialize`, `notifications/initialized`, `tools/list`, and `tools/call` requests over HTTP POST.
- Exposes exactly one tool named `solve_challenge` with no required input properties.
- On every call, reads `X-Exam-Challenge` from the current HTTP request headers and returns one MCP text content item containing the first 16 lowercase hex characters of `SHA-256(challenge:normalized-email)`.
- The challenge value is not accepted from tool arguments.
