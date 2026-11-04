from langgraph.runtime	import Runtime

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import MCP_CLIENT_REGISTRY

import logging


LOGGER = logging.getLogger("MCPAdapter")


async def inject_mcp_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""把 MCP server 的工具追加进本轮 tool_surface"""
	
	client_registry = store_recall(MCP_CLIENT_REGISTRY)
	tool_surface	= runtime.context["tool_surface"]
	
	for tool in await client_registry.get_tools():
		
		# 打一行 warning 不拦截
		if tool_surface.contains(tool):
			LOGGER.warning(f"mcp 工具 '{tool.name}' 已顶替同名工具")
		
		tool_surface.add(tool)