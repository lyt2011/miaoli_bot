from langgraph.runtime	import Runtime

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..consts	import PLUGIN_CONFIG

import logging


LOGGER = logging.getLogger("ToolPermissionManager")


async def pick_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""通过 config.yaml 的权限控制摘除工具"""
	
	config = store_recall(PLUGIN_CONFIG)
	
	# 拿 tool_surface 并构建工具名与权限的映射表
	tool_surface	= runtime.context["tool_surface"]
	tp_mapping		= {p.name: p.mode for p in config.permissions} # 工具名与权限的映射表

	for tool in tool_surface.tools:
		
		# 同意则跳过
		if tp_mapping.get(tool.name) == "allow":
			continue
		
		# 提醒没有配置权限则默认摘除
		if tool.name not in tp_mapping:
			if config.debug: # debug = True 才提醒
				LOGGER.warning(f"{tool.name} 未配置权限 默认摘除")
		
		# 摘除工具
		tool_surface.delete(tool)
	
	return None