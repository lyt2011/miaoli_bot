from langchain_core.messages	import HumanMessage

from langgraph.runtime	import Runtime
from langgraph.config	import get_config

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from ..utils	import build_time_prompt
from ..consts	import DEFAULT_TEMPLATE, LAST_INJECTED_AT, PLUGIN_CONFIG, TAG

from typing		import Any, Dict, Optional
from datetime	import datetime, timedelta


async def time_inject(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Dict[str, Any]]:
	
	"""按 thread_id 需求注入当前时间"""
	
	config	= store_recall(PLUGIN_CONFIG)
	mapping	= store_recall(LAST_INJECTED_AT)
	
	tid		= get_config()["configurable"]["thread_id"]
	now		= datetime.now()
	last_at	= mapping.get(tid)
	
	# 还没超过间隔则不注入
	if last_at and last_at > (now - timedelta(seconds=config.interval)):
		return None
	
	# 更改最后注入时机
	mapping.update({tid: now})
	
	# 优先使用外部文件提示词
	if (path := config.template) and path.is_file():
		prompt = build_time_prompt(path.read_text(encoding=config.encoding), now)
	
	else:
		prompt = build_time_prompt(DEFAULT_TEMPLATE, now)
	
	# 超过间隔或压根没注入过则注入
	return {"messages": HumanMessage(f"<{TAG}>\n{prompt}\n</{TAG}>")}
