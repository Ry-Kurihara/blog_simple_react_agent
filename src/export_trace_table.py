"""
LangfuseトレースデータをMarkdown表形式で出力するスクリプト

指定されたタグでトレースをフィルタリングし、質問文、Output、LLM Judgeスコアを
Markdown表形式で出力します。

実行方法:
    python src/export_trace_table.py --tags 003 nano
    python src/export_trace_table.py --tags brave correctness --output results.md
"""

import os
import argparse
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from langfuse import Langfuse

logger = logging.getLogger("trace.exporter")


def get_traces_by_tags(langfuse_client: Langfuse, tags: List[str], limit: int = 50) -> List[Any]:
    """
    指定されたタグでトレースを取得

    Args:
        langfuse_client: Langfuseクライアント
        tags: フィルタリングするタグのリスト
        limit: 1ページあたりの取得件数

    Returns:
        トレースのリスト
    """
    all_traces = []
    page = 1

    logger.info(f"トレースを取得中... (tags={tags})")

    while True:
        traces = langfuse_client.api.trace.list(
            tags=tags,
            limit=limit,
            page=page
        )

        if not traces.data:
            break

        all_traces.extend(traces.data)
        logger.info(f"  Page {page}: {len(traces.data)} traces")
        page += 1

    logger.info(f"合計 {len(all_traces)} トレースを取得しました")
    return all_traces


def extract_trace_data(traces: List[Any], langfuse_client: Langfuse) -> List[Dict[str, Any]]:
    """
    トレースから質問文、Output、スコアを抽出

    Args:
        traces: トレースのリスト
        langfuse_client: Langfuseクライアント（スコア取得に使用）

    Returns:
        抽出されたデータのリスト
    """
    trace_data = []

    for trace in traces:
        # 質問文を取得（最初のHumanMessageから）
        query = "N/A"
        output = "N/A"

        if hasattr(trace, 'input') and trace.input:
            # inputから質問文を抽出
            if isinstance(trace.input, dict):
                if 'messages' in trace.input and len(trace.input['messages']) > 0:
                    first_message = trace.input['messages'][0]
                    if isinstance(first_message, dict) and 'content' in first_message:
                        content = first_message['content']
                        if isinstance(content, list) and len(content) > 0:
                            query = content[0].get('text', 'N/A')
                        elif isinstance(content, str):
                            query = content

        # Outputを取得（最後のAIMessageから）
        if hasattr(trace, 'output') and trace.output:
            if isinstance(trace.output, dict):
                if 'messages' in trace.output and len(trace.output['messages']) > 0:
                    last_message = trace.output['messages'][-1]
                    if isinstance(last_message, dict) and 'content' in last_message:
                        output = last_message['content']

        # LLM Judgeスコアと理由を取得
        llm_judge_score = None
        llm_judge_reason = None
        if hasattr(trace, 'scores') and trace.scores:
            # scoresはIDのリストなので、各IDからスコア情報を取得
            for score_id in trace.scores:
                if isinstance(score_id, str):
                    try:
                        score = langfuse_client.api.score.get_by_id(score_id)
                        if hasattr(score, 'value') and score.value is not None:
                            llm_judge_score = score.value
                            # commentフィールドから理由を取得
                            if hasattr(score, 'comment') and score.comment:
                                llm_judge_reason = score.comment
                            break
                    except Exception as e:
                        logger.warning(f"スコアID {score_id} の取得に失敗: {e}")
                        continue

        trace_data.append({
            'trace_id': trace.id,
            'query': query,
            'output': output,
            'llm_judge': llm_judge_score,
            'llm_judge_reason': llm_judge_reason,
            'timestamp': trace.timestamp
        })

    # タイムスタンプでソート
    trace_data.sort(key=lambda x: x['timestamp'])

    return trace_data


def generate_markdown_sections(trace_data: List[Dict[str, Any]]) -> str:
    """
    トレースデータからMarkdownセクション形式を生成

    Args:
        trace_data: トレースデータのリスト

    Returns:
        Markdownセクションの文字列
    """
    if not trace_data:
        return "データがありません。"

    sections = []

    for idx, data in enumerate(trace_data, 1):
        # 各トレースをセクションとして出力
        section = f"## Trace{idx}\n\n"

        # Input
        section += f"### Input\n{data['query']}\n\n"

        # Output
        section += f"### Output\n{data['output']}\n\n"

        # Score
        section += f"### Score\n\n"
        if data['llm_judge'] is not None:
            section += f"**LLM Judge**: {data['llm_judge']:.4f}\n\n"

            # LLM Judge Reasonを追加
            if data.get('llm_judge_reason'):
                section += f"**LLM Judge Reason**:\n{data['llm_judge_reason']}\n\n"

            section += f"**Human Judge**: \n\n"
        else:
            section += f"**LLM Judge**: N/A\n\n"
            section += f"**Human Judge**: \n\n"

        sections.append(section)

    return "\n".join(sections)


def main(tags: List[str], output_file: str = "output.md"):
    """
    メイン実行関数

    Args:
        tags: フィルタリングするタグのリスト
        output_file: 出力ファイル名
    """
    logger.info(f"トレースのMarkdown表出力を開始します")
    logger.info(f"  Tags: {tags}")
    logger.info(f"  Output: {output_file}")

    # Langfuseクライアントの初期化
    langfuse = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
    )

    # トレースを取得
    traces = get_traces_by_tags(langfuse, tags)

    if not traces:
        logger.warning("指定されたタグに一致するトレースが見つかりませんでした")
        return

    # データを抽出
    trace_data = extract_trace_data(traces, langfuse)

    # Markdownセクションを生成
    markdown = generate_markdown_sections(trace_data)

    # ファイルに出力
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Langfuse トレース評価結果\n\n")
        f.write(f"**Tags**: {', '.join(tags)}\n\n")
        f.write(markdown)

    logger.info(f"\n✓ Markdownファイルを '{output_file}' に出力しました")
    logger.info(f"  トレース数: {len(trace_data)}")


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 環境変数読み込み
    load_dotenv()

    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(
        description='LangfuseトレースデータをMarkdown表形式で出力',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 複数タグで絞り込み
  python src/export_trace_table.py --tags 003 nano

  # 出力ファイル名を指定
  python src/export_trace_table.py --tags brave correctness --output results.md
        """
    )
    parser.add_argument(
        '--tags',
        nargs='+',
        required=True,
        help='フィルタリングするタグ（複数指定可能）'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output.md',
        help='出力ファイル名（デフォルト: output.md）'
    )
    args = parser.parse_args()

    # 実行
    main(tags=args.tags, output_file=args.output)
