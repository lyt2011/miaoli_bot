from langchain_mcp_adapters.client	import MultiServerMCPClient

from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import MEDIUM, ON_AGENT_START
from miaoli_bot.api		import store_set, get_handler_registry

from .models	import PluginConfig
from .core		import MCPClientRegistry
from .nodes		import inject_mcp_tools
from .consts	import PLUGIN_CONFIG, RAW_CONFIG, MCP_CLIENT_REGISTRY


class MCPAdapter(PluginProtocol):
	
	"""MCP 适配 —— 接入 MCP server 并把其工具注册进工具表"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		handler_registry = get_handler_registry()
		config = PluginConfig.model_validate(self.config)
		
		client_registry = MCPClientRegistry()
		
		
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		self.undo_list.append(store_set(MCP_CLIENT_REGISTRY, client_registry))
		
		# 不启用直接跳过节点/工具注册
		if not config.enable:
			return None
		
		# 在 on_load 构造 mcp 客户端并注册
		for mcp in config.mcps:
			
			mcp_arg	= {mcp.name: mcp.transport.model_dump()}
			client	= MultiServerMCPClient(mcp_arg, tool_name_prefix=config.tool_prefix)
			
			client_registry.register_client(client, reusable=mcp.reusable)
		
		self.undo_list.append(handler_registry.on(ON_AGENT_START, inject_mcp_tools, priority=MEDIUM))
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
