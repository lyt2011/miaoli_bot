from miaoli_bot.api		import get_admin_id, get_bot_id, get_admin_nickname, get_bot_nickname
from miaoli_bot.models	import GraphRuntimeContext, GraphState
from langgraph.runtime	import Runtime
from typing				import Dict, Any


async def inject_account(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""给系统提示词注入账号信息"""
	
	account_info = (
		f"\nadministrator id: {get_admin_id()}"
		f"\nadministrator nickname: {get_admin_nickname()}"
		f"\nbot id: {get_bot_id()}"
		f"\nbot nickname: {get_bot_nickname()}\n"
	)

	return {"prompts": {"account_info": account_info}}
