from miaoli_bot			import GraphRuntimeContext, GraphState, SHARE_STORE
from miaoli_bot.consts	import PLUGIN_CONFIG
from langgraph.runtime	import Runtime
from typing				import Dict, Any


async def inject_account(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""给系统提示词注入账号信息"""

	cfg		= SHARE_STORE.recall(PLUGIN_CONFIG)
	account	= cfg.account

	account_info = "\n".join([
		f"<administrator_QQ_number>{account.admin_id}</administrator_QQ_number>",
		f"<administrator_nickname>{account.admin_nickname}</administrator_nickname>",
		f"<bot_QQ_number>{account.bot_id}</bot_QQ_number>",
		f"<bot_nickname>{account.bot_nickname}</bot_nickname>",
	])

	return { "system_prompt": "\n\n".join([account_info, cfg.system_prompt]) }