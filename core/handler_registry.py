from langgraph.runtime	import Runtime
from langgraph.typing	import StateT, ContextT

from ..consts		import GRAPH_PIPELINE
from ._share_store	import SHARE_STORE

from typing	import Any, Awaitable, Callable, Dict


Node = Callable[[StateT, Runtime[ContextT]], Awaitable[Dict[str, Any]]]


class HandlerRegistry:
	
	"""
	事件处理器注册入口
	目前暂时没有框架 disposer 兜底和 event 校验 现在懒得搞，后续会加上😵
	"""
	
	def on(self, event: str, func: Node, priority: int = 0) -> Callable[[], None]:
		
		"""事件处理器注册 返回 disposer"""
		
		# 拿 pipeline 并注册处理器
		pipeline	= SHARE_STORE.recall(GRAPH_PIPELINE)
		disposer	= pipeline.register_handler(event=event, func=func, priority=priority)
		
		return disposer
