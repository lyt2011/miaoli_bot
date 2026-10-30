from langgraph.runtime			import Runtime
from langchain_core.messages	import HumanMessage

from miaoli_bot.api		import store_recall
from miaoli_bot.models	import GraphRuntimeContext, GraphState

from miaoli_pipeline.actions	import Abort

from typing	import Any, Dict, Optional, Union
from json	import dumps

from ..consts	import EVENT_PARSER

import logging


LOGGER	= logging.getLogger("OB11Adapter")


async def event_adapter(state: GraphState, runtime: Runtime[GraphRuntimeContext]) -> Optional[Union[Dict[str, Any], Abort]]:
	
	"""通过 chain 解析事件并写入 messages"""
	
	# 有事件才解析 没有事件跳过解析而不是丢弃
	if (event := state.get("event")) is None:
		
		LOGGER.warning(f"没有可用 event 对象 跳过 ob11 解析")
		return None
	
	# 解析事件 DispatchResult 可能没有/无效
	dispatch_result	= await store_recall(EVENT_PARSER).dispatch(event)
	if dispatch_result.result is None:
		return Abort()
	
	# 构建 event json
	event_json = dumps(dispatch_result.result, indent=2, ensure_ascii=False)
	
	# 返回 HumanMessage 增量
	return {"event": dispatch_result.result, "messages": [HumanMessage(event_json)]}
