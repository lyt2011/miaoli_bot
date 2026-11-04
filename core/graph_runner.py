from ._share_store	import SHARE_STORE
from ..consts		import INVOKE_LOCK, GRAPH_PIPELINE

from typing	import Any, Dict, Union


async def safe_run_graph(state: Dict[str, Any], thread_id: str, context: Dict[str, Any]) -> Union[Exception, Dict[str, Any]]:
	
	"""并发安全+异常安全的跑图"""
	
	try:
		state = await _run_graph_with_lock(
			state, thread_id=thread_id, context=context)
	
	except Exception as exception:
		return exception
	
	return state

async def _run_graph_with_lock(*args, **kwargs) -> Dict[str, Any]:
	async with SHARE_STORE.recall(INVOKE_LOCK):
		return await SHARE_STORE.recall(GRAPH_PIPELINE).ainvoke(*args, **kwargs)
