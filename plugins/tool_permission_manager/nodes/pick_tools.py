from miaoli_bot.api		import get_admin_id, store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from typing					import List
from langgraph.runtime		import Runtime
from langchain_core.tools	import BaseTool

from ..consts				import PLUGIN_CONFIG
from ..models.permission	import Permission

import logging	


LOGGER = logging.getLogger("ToolPermissionManager")


def is_allowed(permission: Permission, user_id: str, admin_id: str) -> bool:
	
	"""5种权限的统一判定"""
	
	if permission.permission == "admin":
		return user_id == admin_id
	
	if permission.permission == "passerby":
		return user_id != admin_id
	
	if permission.permission == "white_list":
		return user_id in permission.white_list
	
	if permission.permission == "nobody":
		return False
	
	# 这是 anyone
	return True


async def pick_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""通过 config.yaml 的权限控制摘除工具"""
	
	plugin_config	= store_recall(PLUGIN_CONFIG)
	admin_id		= str(get_admin_id())	# 管理员身份取自 miaoli_bot 根配置
	user_id			= str(state["event"]["sender"]["user_id"])
	
	permissions		= {p.tool_name: p for p in plugin_config.permissions}
	
	final_tools: List[BaseTool] = []
	
	for tool in runtime.context["tools"]:
		
		# 对于未配置权限的工具 打印警告日志(仅调试模式)
		if not (permission := permissions.get(tool.name)):
			
			# 突然发现 debug = false 时全部工具都没有权限控制了😅 单独分支检查
			if plugin_config.debug:
				LOGGER.warning(f"{tool.name} 未配置权限 将隐藏该工具")
			
			continue
		
		if is_allowed(permission, user_id, admin_id):
			final_tools.append(tool)
	
	runtime.context["tools"] = final_tools
