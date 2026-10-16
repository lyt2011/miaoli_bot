from langgraph.runtime			import Runtime
from langchain_core.messages	import HumanMessage
from typing						import Any, Dict, Union
from json						import dumps

from miaoli_bot			import GraphRuntimeContext, GraphState, SHARE_STORE
from miaoli_bot.core	import Abort

from ..consts	import EVENT_PARSER


async def event_adapter(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Union[Dict[str, Any], Abort]:
	
	"""通过 chain 解析事件并写入 messages"""
	
	if (event := state.get("event")) is None:
		return Abort(reason="上下文里没有 event 对象")
	
	# 解析事件 DispatchResult 可能没有/无效
	dispatch_result	= await SHARE_STORE.recall(EVENT_PARSER).dispatch(event)
	event_data		= dispatch_result.result
	if event_data is None:
		return Abort()
	
	# 回填 event 字典并返回 HumanMessage 增量
	event_json = dumps(event_data, indent=2, ensure_ascii=False)
	return {"event": event_data, "messages": [HumanMessage(event_json)]}
