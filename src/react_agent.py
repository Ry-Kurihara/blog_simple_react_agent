import logging
import operator
import os
import json
from dotenv import load_dotenv
from typing import Annotated, List, TypedDict, Any, Dict

from langchain_openai import AzureChatOpenAI
from langchain_community.tools import BraveSearch
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_tavily import TavilySearch

from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from langfuse import Langfuse
from langfuse.callback import CallbackHandler


logger = logging.getLogger("websearch.agent")

class SubGraphState(TypedDict, total=False):
    messages: Annotated[List[AnyMessage], operator.add]

class WebSearchAgent:
    def __init__(self) -> None:
        self._langfuse_handler = self._build_langfuse_handler()
        self._llm = self._build_llm()
        self._mcp_config = self._load_mcp_config()

    def _build_llm(self):
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
        ]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise RuntimeError(f"必要な環境変数が設定されていません: {missing_vars}")

        llm = AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        )
        logger.info("AzureChatOpenAI initialized successfully.")
        return llm
    
    def _build_langfuse_handler(self):
        """Langfuse CallbackHandlerを初期化"""
        try:
            Langfuse(
                public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
                secret_key=os.environ["LANGFUSE_SECRET_KEY"],
                host=os.environ.get("LANGFUSE_HOST", "https://api.langfuse.com")
            )
            handler = CallbackHandler()
            logger.info("Langfuse CallbackHandler initialized successfully.")
            return handler
        except KeyError as exc:
            logger.warning(f"Langfuse環境変数が設定されていません: {exc}. トレースは無効です。")
            return None
        except Exception as exc:
            logger.warning(f"Langfuse初期化に失敗しました: {exc}. トレースは無効です。")
            return None
    
    def _load_mcp_config(self) -> List[Dict[str, Any]]:
        with open("src/mcp_config.json") as f:
            return json.load(f)["mcpServers"]

        message = [
            SystemMessage(content=content),
            MessagesPlaceholder("messages"),
        ]
        prompt = ChatPromptTemplate.from_messages(message)
        return prompt
    
    def create_brave_search_tool(self) -> BraveSearch:
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            logger.warning("BRAVE_API_KEY is not set. BraveSearch tool will not be available.")
        else:
            logger.info(f"BraveSearch initialized with API key: {api_key[:10]}***")

        tool = BraveSearch.from_api_key(api_key=api_key)
        logger.info(f"BraveSearch tool created: {tool.name}")
        return tool
    
    def create_tavily_search_tool(self) -> TavilySearch:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.warning("TAVILY_API_KEY is not set. TavilySearch tool will not be available.")
            raise ValueError("TAVILY_API_KEY environment variable is required")
        else:
            logger.info(f"TavilySearch initialized with API key: {api_key[:10]}***")

        # TavilySearchは環境変数TAVILY_API_KEYから自動的にAPIキーを読み込む
        tool = TavilySearch()
        logger.info(f"TavilySearch tool created: {tool.name}")
        return tool
    
    def build_simple_graph(self, llm, tools: List) -> CompiledGraph:
        simple_graph = create_react_agent(model=llm, tools=tools)
        return simple_graph
    
    async def terminal_interface(self, graph: CompiledStateGraph, graph_config):
        print("終了するには 'exit' と入力してください。")
        while True:
            user_input = input("ユーザ: ")
            if user_input.lower() == "exit":
                break
            input_query = [HumanMessage(
                [
                    {
                        "type": "text",
                        "text": f"{user_input}"
                    },
                ]
            )]
            logger.info(f"User query: {user_input}")
            response = await graph.ainvoke({"messages":input_query}, graph_config)

            #デバック用
            logger.info(f"Final response message count: {len(response['messages'])}")
            logger.debug("response: %s", response)

            # 最終的な回答
            print("=================================")
            print(response["messages"][-1].content)
            print("=================================")

    async def simple_interface(self, graph: CompiledStateGraph, graph_config, query: str):
        input_query = [HumanMessage(
                [
                    {
                        "type": "text",
                        "text": f"{query}"
                    },
                ]
            )]

        logger.info(f"User query: {query}")
        response = await graph.ainvoke({"messages":input_query}, graph_config)

        #デバック用
        logger.info(f"Final response message count: {len(response['messages'])}")
        logger.debug("response: %s", response)

        # 最終的な回答
        print("=================================")
        print(response["messages"][-1].content)
    
    async def main(self, query: str = None, use_mcp: bool = False, graph_config = {"configurable": {"thread_id": "12345"}}):
        tools = []

        if use_mcp:
            if not self._mcp_config:
                raise ValueError("MCP config is not loaded.")
            mcp_client = MultiServerMCPClient(self._mcp_config)
            mcp_tools = await mcp_client.get_tools()
            tools.extend(mcp_tools)
            logger.info(f"MCP tools loaded: {[tool.name for tool in mcp_tools]}")

        # tools.append(self.create_brave_search_tool())
        tools.append(self.create_tavily_search_tool())
        logger.info(f"Loaded {len(tools)} tools: {[tool.name for tool in tools]}")

        graph = self.build_simple_graph(llm=self._llm, tools=tools)

        # datasetフィールドはLangfuseで自動評価のデータ仕分けに使用する
        graph_config = {"configurable": {"thread_id": "12345", "dataset": "score-2"}, "callbacks": [self._langfuse_handler]}

        if query:
            # コマンドライン引数で質問が渡された場合
            await self.simple_interface(graph, graph_config, query)
        else:
            # 対話モード
            await self.terminal_interface(graph, graph_config)
        

if __name__ == "__main__":
    import asyncio
    import argparse

    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description='Web検索エージェント')
    parser.add_argument('query', nargs='?', help='検索クエリ（省略時は対話モード）')
    parser.add_argument('--use-mcp', action='store_true', default=False, help='MCPツールを使用する（デフォルト: False）')
    args = parser.parse_args()

    agent = WebSearchAgent()
    asyncio.run(agent.main(query=args.query, use_mcp=args.use_mcp))