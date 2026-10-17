from miaoli_bot	import GraphRuntimeContext, GraphState, SHARE_STORE

from typing							import Dict
from langgraph.runtime				import Runtime
from langchain_core.tools			import BaseTool

from ..consts	import MCP_CLIENT_REGISTRY


async def recall_mcp_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""召唤 mcp 工具"""
	
	client_registry = SHARE_STORE.recall(MCP_CLIENT_REGISTRY)
	
	# 获取工具
	mcp_tools: Dict[str, BaseTool] = {tool.name: tool for tool in await client_registry.get_tools()}
	raw_tools: Dict[str, BaseTool] = {tool.name: tool for tool in runtime.context.get("tools", [])}
	
	# FIXME: 这里只能实现去重但没法实现过滤下架的
	raw_tools.update(mcp_tools)
	runtime.context["tools"] = list(raw_tools.values())
