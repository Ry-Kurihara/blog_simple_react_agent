#!/bin/bash

# Fishing MCP - Streamable HTTP テストスクリプト

# 設定
HOST="localhost"
PORT="5555"
URL="http://${HOST}:${PORT}/mcp"
AUTH_USER="fishing_user"
AUTH_PASS="fishing_test_password_2025"

echo "=== Fishing MCP Streamable HTTP Test ==="
echo "URL: ${URL}"
echo ""

# Basic認証の有無を確認
if [ -n "$AUTH_USER" ] && [ -n "$AUTH_PASS" ]; then
    AUTH_HEADER="Authorization: Basic $(echo -n ${AUTH_USER}:${AUTH_PASS} | base64)"
    echo "Basic Auth: Enabled"
else
    AUTH_HEADER=""
    echo "Basic Auth: Disabled"
fi

echo ""
echo "=== Test 1: Initialize Request ==="
echo ""

INIT_RESPONSE=$(curl -s -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }')

echo "$INIT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$INIT_RESPONSE"

echo ""
echo "=== Test 2: List Tools Request ==="
echo ""

TOOLS_RESPONSE=$(curl -s -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }')

echo "$TOOLS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOOLS_RESPONSE"

echo ""
echo "=== Test 3: Call list_spots Tool ==="
echo ""

LIST_SPOTS_RESPONSE=$(curl -s -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "list_spots",
      "arguments": {}
    }
  }')

echo "$LIST_SPOTS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LIST_SPOTS_RESPONSE"

echo ""
echo "=== Test 4: Unauthorized Request (without auth) ==="
echo ""

UNAUTH_RESPONSE=$(curl -s -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/list"
  }')

echo "Response: $UNAUTH_RESPONSE"

echo ""
echo "=== Tests Completed ==="
