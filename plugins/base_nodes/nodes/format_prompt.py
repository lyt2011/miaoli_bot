from miaoli_bot			import GraphRuntimeContext, GraphState
from langgraph.runtime	import Runtime
from typing				import Dict, Any


async def format_prompt(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Dict[str, Any]:

	"""拼接账号信息与系统提示词"""

	cfg		= runtime.context["plugin_config"]
	account	= cfg.account

	account_info = "\n".join([
		f"<administrator_QQ_number>{account.admin_id}</administrator_QQ_number>",
		f"<administrator_nickname>{account.admin_nickname}</administrator_nickname>",
		f"<bot_QQ_number>{account.bot_id}</bot_QQ_number>",
		f"<bot_nickname>{account.bot_nickname}</bot_nickname>",
	])

	return {"system_prompt": "\n".join([account_info, cfg.system_prompt])}