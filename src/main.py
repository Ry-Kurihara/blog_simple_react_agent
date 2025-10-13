"""
評価実行用ラッパースクリプト

このスクリプトは、evaluation_dataset.yamlに定義された質問セットを使用して、
BraveSearchとTavilySearchの性能を比較評価します。

実行方法:
    python src/main.py --tool brave
    python src/main.py --tool tavily
"""

import asyncio
import argparse
import logging
import yaml
from typing import Dict, List, Any
from react_agent import WebSearchAgent

logger = logging.getLogger("evaluation.runner")


def load_evaluation_dataset(filepath: str = "src/evaluation_dataset.yaml") -> Dict[str, Any]:
    """評価データセットをYAMLファイルから読み込む"""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run_evaluation_set(
    agent: WebSearchAgent,
    evaluation_set: Dict[str, Any],
    tool_name: str,
    use_mcp: bool = False
) -> List[Dict[str, Any]]:
    """
    1つの評価セット（5問）を実行する

    Args:
        agent: WebSearchAgent インスタンス
        evaluation_set: 評価セットの辞書
        tool_name: 使用するツール名（brave/tavily）
        use_mcp: MCPツールを使用するか

    Returns:
        各質問の実行結果リスト
    """
    template_name = evaluation_set["evaluation_template"]
    questions = evaluation_set["questions"]

    logger.info(f"=" * 60)
    logger.info(f"評価テンプレート: {template_name}")
    logger.info(f"質問数: {len(questions)}")
    logger.info(f"使用ツール: {tool_name}")
    logger.info(f"=" * 60)

    results = []

    for idx, question_data in enumerate(questions, 1):
        query = question_data["query"]
        expected_info = question_data.get("expected_info", "")

        logger.info(f"\n[質問 {idx}/{len(questions)}]")
        logger.info(f"Query: {query}")
        logger.info(f"Expected: {expected_info}")

        try:
            # graph_configのdatasetフィールドをツール名に設定
            graph_config = {
                "configurable": {
                    "thread_id": f"{tool_name}_{template_name}_{idx}",
                    "dataset": tool_name  # brave or tavily
                },
                "callbacks": [agent._langfuse_handler] if agent._langfuse_handler else []
            }

            # react_agentを使用して質問を実行
            from langchain_core.messages import HumanMessage
            input_query = [HumanMessage([{"type": "text", "text": query}])]

            # ツールの準備
            tools = []
            if use_mcp:
                from langchain_mcp_adapters.client import MultiServerMCPClient
                if agent._mcp_config:
                    mcp_client = MultiServerMCPClient(agent._mcp_config)
                    mcp_tools = await mcp_client.get_tools()
                    tools.extend(mcp_tools)

            # ツール名に応じて適切な検索ツールを追加
            if tool_name == "brave":
                tools.append(agent.create_brave_search_tool())
            elif tool_name == "tavily":
                tools.append(agent.create_tavily_search_tool())
            else:
                raise ValueError(f"Unknown tool name: {tool_name}")

            # グラフの構築
            graph = agent.build_simple_graph(llm=agent._llm, tools=tools)

            # 実行
            response = await graph.ainvoke({"messages": input_query}, graph_config)

            # 結果を記録
            result = {
                "question_index": idx,
                "query": query,
                "expected_info": expected_info,
                "response": response["messages"][-1].content,
                "message_count": len(response["messages"]),
                "tool": tool_name,
                "template": template_name
            }
            results.append(result)

            logger.info(f"✓ 完了: {len(response['messages'])} メッセージ")

        except Exception as e:
            logger.error(f"✗ エラー: {e}")
            results.append({
                "question_index": idx,
                "query": query,
                "error": str(e),
                "tool": tool_name,
                "template": template_name
            })

    return results


async def main(tool_name: str, use_mcp: bool = False):
    """
    メイン実行関数

    Args:
        tool_name: 使用するツール名（brave/tavily）
        use_mcp: MCPツールを使用するか
    """
    logger.info(f"評価実行開始: tool={tool_name}, use_mcp={use_mcp}")

    # 評価データセットを読み込み
    dataset = load_evaluation_dataset()
    evaluation_sets = dataset["evaluation_sets"]

    logger.info(f"評価セット数: {len(evaluation_sets)}")
    logger.info(f"総質問数: {dataset['metadata']['total_questions']}")

    # WebSearchAgentの初期化
    from dotenv import load_dotenv
    load_dotenv()
    agent = WebSearchAgent()

    # 各評価セットを実行
    all_results = []
    for eval_set in evaluation_sets:
        results = await run_evaluation_set(agent, eval_set, tool_name, use_mcp)
        all_results.extend(results)

    # 結果サマリー
    logger.info(f"\n{'=' * 60}")
    logger.info(f"評価実行完了")
    logger.info(f"総実行数: {len(all_results)}")
    success_count = sum(1 for r in all_results if "error" not in r)
    error_count = sum(1 for r in all_results if "error" in r)
    logger.info(f"成功: {success_count}, エラー: {error_count}")
    logger.info(f"{'=' * 60}")

    # Langfuseでトレースを確認
    logger.info(f"\nLangfuseでトレースを確認してください:")
    logger.info(f"http://localhost:3000/project/cmg4us1cn0001nn073xmqh0p4/traces")
    logger.info(f"dataset={tool_name} でフィルタリングできます")


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description='評価データセット実行ツール')
    parser.add_argument(
        '--tool',
        choices=['brave', 'tavily'],
        required=True,
        help='使用する検索ツール (brave or tavily)'
    )
    parser.add_argument(
        '--use-mcp',
        action='store_true',
        default=False,
        help='MCPツールを使用する（デフォルト: False）'
    )
    args = parser.parse_args()

    # 実行
    asyncio.run(main(tool_name=args.tool, use_mcp=args.use_mcp))
