# Fishing MCP Server

釣り計画の意思決定を支援するMCP（Model Context Protocol）サーバー。
天気、潮汐、日の出・日の入り情報を統合し、LLMエージェントから利用可能なツールとして提供します。

## 概要

このMCPサーバーは、以下の機能を提供します：

- **釣りスポット情報の管理**: 是政橋、天空橋、羽田河口などの釣り場情報
- **天気情報の取得**: Open-Meteo APIを使用した時間ごとの天気予報
- **潮汐情報の取得**: Tide736.net APIを使用した満潮・干潮情報
- **日の出・日の入り情報**: 太陽の時刻情報
- **釣りプランの生成**: 上記の情報を統合した釣りセッションの提案

## アーキテクチャ

```
server/fishing_mcp/
├── config/
│   └── spots.json          # 釣りスポット定義
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py            # FastMCPサーバー本体
│   ├── models.py            # データモデル定義
│   ├── weather_client.py    # Open-Meteo APIクライアント
│   └── tide_client.py       # Tide736 APIクライアント
└── requirements.txt
```

## 提供ツール

### 1. `list_spots`
登録済みの釣りスポット一覧を取得します。

**パラメータ**: なし

**戻り値**: スポット一覧（JSON）

### 2. `get_spot_info`
特定の釣りスポットの詳細情報を取得します。

**パラメータ**:
- `spot_id` (string): スポットID（例: "korose_bridge", "tenkukyo"）

**戻り値**: スポット詳細情報（JSON）

### 3. `get_weather`
指定スポットの天気情報を取得します。

**パラメータ**:
- `spot_id` (string): スポットID
- `start` (string): 開始日時（ISO8601形式、例: "2025-11-30T05:00:00+09:00"）
- `end` (string): 終了日時（ISO8601形式、例: "2025-11-30T10:00:00+09:00"）

**戻り値**: 天気情報のリスト（気温、風速、降水量など）

### 4. `get_tide`
指定スポットの潮汐情報を取得します。

**パラメータ**:
- `spot_id` (string): スポットID
- `target_date` (string): 対象日（YYYY-MM-DD形式、例: "2025-11-30"）

**戻り値**: 満潮・干潮イベントのリスト

### 5. `get_sun_times`
指定スポットの日の出・日の入り情報を取得します。

**パラメータ**:
- `spot_id` (string): スポットID
- `target_date` (string): 対象日（YYYY-MM-DD形式）

**戻り値**: 日の出・日の入り時刻

### 6. `plan_fishing_session`
釣りセッションの総合的なプランを生成します（高レベルツール）。

**パラメータ**:
- `spot_id` (string): スポットID
- `target_date` (string): 対象日（YYYY-MM-DD形式）
- `time_window_start` (string): 時間範囲の開始（HH:MM形式、例: "05:00"）
- `time_window_end` (string): 時間範囲の終了（HH:MM形式、例: "10:00"）
- `target_fish` (string, optional): 対象魚種（例: "bass", "seabass"）

**戻り値**: 釣りプラン提案（推奨時間帯、戦術、ルアー候補、リスク情報など）

## セットアップ

### 依存パッケージのインストール

```bash
pip install -r server/fishing_mcp/requirements.txt
```

### MCPサーバーの起動

#### stdio モード（デフォルト）

```bash
python -m server.fishing_mcp.src.server
```

または環境変数で明示的に指定：

```bash
MCP_TRANSPORT=stdio python -m server.fishing_mcp.src.server
```

#### streamable-http モード（将来対応予定）

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=5555 python -m server.fishing_mcp.src.server
```

#### SSE モード（将来対応予定）

```bash
MCP_TRANSPORT=sse MCP_HOST=0.0.0.0 MCP_PORT=5555 python -m server.fishing_mcp.src.server
```

## エージェントとの統合

### mcp_config.json の設定例

```json
{
  "mcpServers": {
    "fishing_mcp": {
      "transport": "stdio",
      "command": ".venv/bin/python",
      "args": [
        "-m",
        "server.fishing_mcp.src.server"
      ]
    }
  }
}
```

### 使用例

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

# MCPクライアントの初期化
mcp_config = {...}  # 上記のmcp_config.json
mcp_client = MultiServerMCPClient(mcp_config)

# ツールの取得
tools = await mcp_client.get_tools()

# エージェントに組み込む
agent = create_react_agent(model=llm, tools=tools)
```

### コマンドライン例

```bash
# 釣りスポット一覧を取得
python src/react_agent.py "釣りスポットの一覧を教えてください" --use-mcp

# 釣り計画を立てる
python src/react_agent.py "明日の朝5時から10時まで、天空橋で釣りをする計画を立ててください" --use-mcp
```

## 使用API

### Open-Meteo（天気情報）
- URL: https://api.open-meteo.com/v1/forecast
- 特徴: APIキー不要、非営利利用無料
- ドキュメント: https://open-meteo.com/

### Tide736.net（潮汐情報）
- URL: https://api.tide736.net/get_tide.php
- 特徴: 日本沿岸736港対応、APIキー不要
- 注意: 個人運営のため、サービス継続性の保証なし

## 既知の問題

1. **日付パースの問題**: 現在、一部の日付が正しく処理されない場合があります（2023年として解釈される）。
2. **Tide736 API**: 301 Moved Permanentlyエラーが発生する場合があります。APIのURLやパラメータの見直しが必要です。
3. **Open-Meteo API**: 一部のリクエストで400 Bad Requestが発生します。パラメータの検証が必要です。

## 今後の改善

- [ ] 日付処理の修正
- [ ] 外部APIエラーハンドリングの強化
- [ ] リトライロジックの追加
- [ ] キャッシング機能の実装
- [ ] streamable-http / SSE トランスポートのテスト
- [ ] Docker化
- [ ] 単体テストの追加
- [ ] より多くの釣りスポットの追加
- [ ] 釣果ログ機能の追加

## ライセンス

本プロジェクトは個人的な学習・実験目的で作成されています。

## 参考資料

- [MCP仕様](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp)
