#!/bin/bash

# Fishing MCP - Streamable HTTP起動スクリプト

# プロジェクトルートに移動
cd "$(dirname "$0")/../.."

# 仮想環境を有効化
source .venv/bin/activate

# .envファイルが存在する場合は読み込む
if [ -f "server/fishing_mcp/.env.streamable-http" ]; then
    echo "Loading environment from .env.streamable-http..."
    export $(cat server/fishing_mcp/.env.streamable-http | grep -v '^#' | xargs)
else
    echo "Warning: .env.streamable-http not found. Using default values."
    echo "You can create it by copying .env.streamable-http.example"

    # デフォルト値を設定
    export MCP_TRANSPORT=streamable-http
    export MCP_HOST=0.0.0.0
    export MCP_PORT=5555
fi

echo "Starting Fishing MCP Server..."
echo "Transport: ${MCP_TRANSPORT}"
echo "Host: ${MCP_HOST}"
echo "Port: ${MCP_PORT}"

if [ -n "$MCP_BASIC_AUTH_USER" ]; then
    echo "Basic Auth: Enabled (User: ${MCP_BASIC_AUTH_USER})"
else
    echo "Basic Auth: Disabled"
fi

echo ""
echo "Server will be available at: http://${MCP_HOST}:${MCP_PORT}/mcp"
echo ""

# サーバーを起動
python -m server.fishing_mcp.src.server
