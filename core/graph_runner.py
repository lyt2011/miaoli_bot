from .share_store	import SHARE_STORE
from ..consts		import INVOKE_LOCKS, GRAPH_PIPELINE

from typing	import Any, Dict, Union


async def safe_run_graph(state: Dict[str, Any], thread_id: str, context: Dict[str, Any]) -> Union[Exception, Dict[str, Any]]:
	
	"""并发安全+异常安全的跑图"""
	
	pipeline	= SHARE_STORE.recall(GRAPH_PIPELINE)
	invoke_lock	= SHARE_STORE.recall(INVOKE_LOCKS)[thread_id]
	
	# 安全的锁内跑图
	try:
		async with invoke_lock:
			state_ = await pipeline.ainvoke(
				state, thread_id=thread_id, context=context)
	
	except Exception as exception:
		return exception
	
	return state_
