from miaoli_bot	import GraphRuntimeContext, GraphState, SHARE_STORE

from typing							import Dict
from langgraph.runtime				import Runtime
from langchain_core.tools			import BaseTool
from langchain_mcp_adapters.client	import MultiServerMCPClient

from ..consts	import PLUGIN_CONFIG


async def recall_mcp_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""召唤 mcp 工具"""
	
	# 获取插件配置
	plugin_cfg = SHARE_STORE.recall(PLUGIN_CONFIG)
	
	# 构建 MCP 客户端
	client = MultiServerMCPClient(
		{
			mcp.name: mcp.transport.model_dump()
			for mcp in plugin_cfg.mcps
		},
		tool_name_prefix = plugin_cfg.tool_prefix
	)
	
	# 获取工具
	mcp_tools: Dict[str, BaseTool] = {tool.name: tool for tool in await client.get_tools()}
	raw_tools: Dict[str, BaseTool] = {tool.name: tool for tool in runtime.context.get("tools", [])}
	
	# FIXME: 这里只能实现去重但没法实现过滤下架的
	raw_tools.update(mcp_tools)
	runtime.context["tools"] = list(raw_tools.values())