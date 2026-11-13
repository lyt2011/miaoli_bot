from langgraph.runtime	import Runtime
from langgraph.config	import get_config

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import PLUGIN_CONFIG
from ..utils	import is_allowed

import logging


LOGGER = logging.getLogger("ToolPermissionManager")


async def pick_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""通过 config.yaml 的权限控制摘除工具"""
	
	# 获取 thread_id
	thread_id	= get_config()["configurable"]["thread_id"]
	
	# 获取配置并构建权限映射表
	config	= store_recall(PLUGIN_CONFIG)
	mapping	= {p.name: p for p in config.permissions}
	
	for tool in runtime.context["tool_surface"].tools:
		
		# 声明了权限且放行则保留
		if tool.name in mapping and is_allowed(thread_id, mapping[tool.name].allowed):
			continue
		
		# 没有声明工具默认摘除 调试模式时需要打日志确认
		if tool.name not in mapping and config.debug is True:
			LOGGER.warning(f"{tool.name} 未声明工具权限 默认摘除")
		
		runtime.context["tool_surface"].delete(tool)
	
	return None
