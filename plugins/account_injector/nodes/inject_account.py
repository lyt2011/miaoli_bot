from miaoli_bot.api		import get_admin_id, get_bot_id, get_admin_nickname, get_bot_nickname, get_prompt
from miaoli_bot.models	import GraphRuntimeContext, GraphState
from langgraph.runtime	import Runtime
from typing				import Dict, Any


async def inject_account(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""给系统提示词注入账号信息"""

	account_info = "\n".join([
		f"<administrator_QQ_number>{get_admin_id()}</administrator_QQ_number>",
		f"<administrator_nickname>{get_admin_nickname()}</administrator_nickname>",
		f"<bot_QQ_number>{get_bot_id()}</bot_QQ_number>",
		f"<bot_nickname>{get_bot_nickname()}</bot_nickname>",
	])

	return { "system_prompt": "\n\n".join([account_info, get_prompt()]) }