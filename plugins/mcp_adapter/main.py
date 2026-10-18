from miaoli_bot.api			import store_drop, store_set
from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.consts		import MEDIUM

from langchain_mcp_adapters.client	import MultiServerMCPClient

from .consts	import PLUGIN_CONFIG, RAW_CONFIG, MCP_CLIENT_REGISTRY
from .core		import MCPClientRegistry
from .models	import PluginConfig
from .nodes		import recall_mcp_tools


# 太长了弄个短点的名字
MSMC = MultiServerMCPClient


class MCPAdapter(PluginProtocol):
	
	"""MCP 适配 —— 接入 MCP server 并把其工具注册进工具表"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = MCPClientRegistry()
		
		store_set(PLUGIN_CONFIG, config)
		store_set(RAW_CONFIG, self.config)
		store_set(MCP_CLIENT_REGISTRY, registry)
		
		# 不启用直接跳过节点/工具注册
		if not config.enable:
			return None
		
		# 在 on_load 构造 mcp 客户端并注册
		for mcp in config.mcps:
			
			mcp_arg	= {mcp.name: mcp.transport.model_dump()}
			client	= MSMC(mcp_arg, tool_name_prefix=config.tool_prefix)
			
			registry.register_client(client, reusable=mcp.reusable)
		
		self.registry.on_before_request(recall_mcp_tools, priority=MEDIUM)
	
	async def on_close(self) -> None:
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
		store_drop(MCP_CLIENT_REGISTRY)
