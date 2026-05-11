#!/bin/bash
HOST="localhost"
PORT="5555"
URL="http://${HOST}:${PORT}/mcp"
AUTH="$(echo -n fishing_user:fishing_test_password_2025 | base64)"

echo "Testing with Accept headers..."
curl -s -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Basic ${AUTH}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 -m json.tool
