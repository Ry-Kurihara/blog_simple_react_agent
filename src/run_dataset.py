"""
評価実行用ラッパースクリプト

このスクリプトは、evaluation_dataset.yamlに定義された質問セットを使用して、
BraveSearchとTavilySearchの性能を比較評価します。

実行方法:
    # デフォルト（Helpfulnessのみ実行）
    python src/run_dataset.py --tool brave

    # 特定の評価指標を実行
    python src/run_dataset.py --tool tavily --metric correctness

    # すべての評価指標を実行
    python src/run_dataset.py --tool brave --metric all
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
    custom_tags: List[str] = None,
    use_mcp: bool = False
) -> List[Dict[str, Any]]:
    """
    1つの評価セット（5問）を実行する

    Args:
        agent: WebSearchAgent インスタンス
        evaluation_set: 評価セットの辞書
        tool_name: 使用するツール名（brave/tavily）
        custom_tags: カスタムタグのリスト
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
    if custom_tags:
        logger.info(f"カスタムタグ: {custom_tags}")
    logger.info(f"=" * 60)

    results = []

    for idx, question_data in enumerate(questions, 1):
        query = question_data["query"]
        expected_info = question_data.get("expected_info", "")

        logger.info(f"\n[質問 {idx}/{len(questions)}]")
        logger.info(f"Query: {query}")
        logger.info(f"Expected: {expected_info}")

        try:
            # タグの構築（デフォルト + カスタム）
            tags = [tool_name, template_name.lower()]
            if custom_tags:
                tags.extend(custom_tags)

            # graph_configの設定
            graph_config = {
                "configurable": {
                    "thread_id": f"{tool_name}_{template_name}_{idx}"
                },
                "tags": tags,  # Tagsを直接設定（metadataではなくRunnableConfigのtags属性）
                "metadata": {
                    "ground_truth": expected_info  # Correctness評価用のground_truth
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


async def main(tool_name: str, metric: str = "helpfulness", custom_tags: List[str] = None, use_mcp: bool = False, deployment_name: str = "gpt-4o"):
    """
    メイン実行関数

    Args:
        tool_name: 使用するツール名（brave/tavily）
        metric: 評価指標（helpfulness/correctness/relevance/all）
        custom_tags: カスタムタグのリスト
        use_mcp: MCPツールを使用するか
        deployment_name: Azure OpenAIのデプロイメント名
    """
    logger.info(f"評価実行開始: tool={tool_name}, metric={metric}, custom_tags={custom_tags}, use_mcp={use_mcp}, deployment={deployment_name}")

    # 評価データセットを読み込み
    dataset = load_evaluation_dataset()
    evaluation_sets = dataset["evaluation_sets"]

    # 評価指標に応じてフィルタリング
    if metric.lower() != "all":
        # 指定された評価指標のみ実行
        metric_normalized = metric.capitalize()  # helpfulness -> Helpfulness
        evaluation_sets = [
            eval_set for eval_set in evaluation_sets
            if eval_set["evaluation_template"].lower() == metric.lower()
        ]
        if not evaluation_sets:
            logger.error(f"指定された評価指標が見つかりません: {metric}")
            logger.info(f"利用可能な評価指標: helpfulness, correctness, relevance, all")
            return

    logger.info(f"評価セット数: {len(evaluation_sets)}")
    total_questions = sum(len(eval_set["questions"]) for eval_set in evaluation_sets)
    logger.info(f"総質問数: {total_questions}")

    # WebSearchAgentの初期化
    from dotenv import load_dotenv
    load_dotenv()
    agent = WebSearchAgent(deployment_name=deployment_name)

    # 各評価セットを実行
    all_results = []
    for eval_set in evaluation_sets:
        results = await run_evaluation_set(agent, eval_set, tool_name, custom_tags, use_mcp)
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
    logger.info(f"tags={tool_name} でフィルタリングできます")


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(
        description='評価データセット実行ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # デフォルト（Helpfulnessのみ実行）
  python src/run_dataset.py --tool brave

  # タグを追加
  python src/run_dataset.py --tool tavily --tags prod experiment-v2

  # 複数タグとmetric指定
  python src/run_dataset.py --tool brave --metric all --tags prod gpt-4o
        """
    )
    parser.add_argument(
        '--tool',
        choices=['brave', 'tavily'],
        required=True,
        help='使用する検索ツール (brave or tavily)'
    )
    parser.add_argument(
        '--metric',
        choices=['helpfulness', 'correctness', 'relevance', 'all'],
        default='helpfulness',
        help='評価指標 (helpfulness/correctness/relevance/all、デフォルト: helpfulness)'
    )
    parser.add_argument(
        '--tags',
        nargs='*',  # 0個以上の引数を受け取る
        default=[],
        help='カスタムタグ（複数指定可能、例: --tags prod experiment-v2）'
    )
    parser.add_argument(
        '--use-mcp',
        action='store_true',
        default=False,
        help='MCPツールを使用する（デフォルト: False）'
    )
    parser.add_argument(
        '--deployment-name',
        type=str,
        default='gpt-4o',
        help='Azure OpenAIのデプロイメント名（デフォルト: gpt-4o, ex: gpt-4.1-nano）'
    )
    args = parser.parse_args()

    # 実行
    asyncio.run(main(
        tool_name=args.tool,
        metric=args.metric,
        custom_tags=args.tags if args.tags else None,
        use_mcp=args.use_mcp,
        deployment_name=args.deployment_name
    ))
