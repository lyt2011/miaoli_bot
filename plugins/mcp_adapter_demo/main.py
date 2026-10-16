from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.stores		import SHARE_STORE
from miaoli_bot.consts		import MEDIUM

from .consts	import PLUGIN_CONFIG, RAW_CONFIG
from .models	import PluginConfig
from .nodes		import recall_mcp_tools


class MCPAdapterDemo(PluginProtocol):
	
	"""MCP 适配演示 —— 接入 MCP server 并把其工具注册进工具表"""
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		SHARE_STORE.set(PLUGIN_CONFIG, config)
		SHARE_STORE.set(RAW_CONFIG, self.config)
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		# 每次请求前重新拉一遍工具 结果追加进 runtime.context["tools"]
		# 必须早于 tool_permission_manager 的 pick_tools(priority=1) 否则 MCP 工具会绕过权限过滤
		self.registry.on_before_request(recall_mcp_tools, priority=MEDIUM)
	
	async def on_close(self) -> None:
		
		SHARE_STORE.drop(PLUGIN_CONFIG)
		SHARE_STORE.drop(RAW_CONFIG)
