from miaoli_bot			import GraphRuntimeContext, GraphState
from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.consts	import PLUGIN_CONFIG as ROOT_PLUGIN_CONFIG

from typing					import List
from ncatbot.utils			import get_log
from langgraph.runtime		import Runtime
from langchain_core.tools	import BaseTool

from ..consts				import PLUGIN_CONFIG
from ..models.permission	import Permission


LOGGER = get_log("ToolPermissionManager")


def is_allowed(permission: Permission, user_id: str, admin_id: str) -> bool:
	
	"""三种权限的统一判定"""
	
	if permission.permission == "admin":
		return user_id == admin_id
	
	if permission.permission == "white_list":
		return user_id in permission.white_list
	
	return True


async def pick_tools(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> None:
	
	"""通过 config.yaml 的权限控制摘除工具"""
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG)
	admin_id		= str(SHARE_STORE.recall(ROOT_PLUGIN_CONFIG).account.admin_id)	# 管理员身份取自 miaoli_bot 根配置
	user_id			= str(state["event"]["sender"]["user_id"])
	
	permissions		= {p.tool_name: p for p in plugin_config.permissions}
	
	final_tools: List[BaseTool] = []
	
	for tool in runtime.context["tools"]:
		
		permission = permissions.get(tool.name)
		
		if permission is None:
			LOGGER.warning(f"{tool.name} 未配置权限 将隐藏该工具")
			continue
		
		if is_allowed(permission, user_id, admin_id):
			final_tools.append(tool)
	
	runtime.context["tools"] = final_tools
