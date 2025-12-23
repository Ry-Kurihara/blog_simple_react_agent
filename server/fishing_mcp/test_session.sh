#!/bin/bash
HOST="localhost"
PORT="5555"
URL="http://${HOST}:${PORT}/mcp"
AUTH="$(echo -n fishing_user:fishing_test_password_2025 | base64)"

echo "=== Step 1: Initialize ===" 
INIT_RESP=$(curl -si -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Basic ${AUTH}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')

echo "$INIT_RESP"
echo ""

# Extract session ID from headers
SESSION_ID=$(echo "$INIT_RESP" | grep -i "mcp-session-id:" | cut -d' ' -f2 | tr -d '\r')

if [ -n "$SESSION_ID" ]; then
    echo "Session ID: $SESSION_ID"
    echo ""
    echo "=== Step 2: List Tools with Session ==="
    curl -s -X POST "${URL}" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -H "Authorization: Basic ${AUTH}" \
      -H "mcp-session-id: ${SESSION_ID}" \
      -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python3 -m json.tool
fi
