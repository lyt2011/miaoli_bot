from pi_bridge.models	import BaseEvent

from ncatbot.utils		import get_log
from collections		import defaultdict
from collections.abc	import AsyncIterator
from typing				import Any, Awaitable, Callable, Dict, List, Self


CALLBACK_TYPE	= Callable[[BaseEvent], Awaitable[Any]]

DISPATCH_LOGGER	= get_log("prompt_dispatcher")


def _handler_name(handler: CALLBACK_TYPE) -> str:
	
	"""回调名（partial / 可调用对象没有 __name__，日志路径不能依赖它）"""
	
	return getattr(handler, "__name__", type(handler).__name__)


class _Prompt:
	
	"""
	prompt 事件流包装
	
	遍历行为与原 prompt 一致（单次消费的异步迭代器），遍历过程中把每个事件
	分发给按类型注册的回调，替代调用后的 if / isinstance 链
	
	- 惰性：构造时不启动底层流，首次 __anext__ 才真正开始执行，
	  因此可以在遍历前随时 register_callback
	- 单消费者：一个 Prompt 只应由一个 Task 遍历
	- 提前退出（break / return）不会收尾底层流，请用 aclose() 或 async with
	"""
	
	def __init__(self, agen: AsyncIterator[BaseEvent]):
		
		self._agen = agen
		
		self.event_handlers: Dict[type[BaseEvent], List[CALLBACK_TYPE]] = defaultdict(list)
	
	def register_callback(self, event_type: type[BaseEvent], handler: CALLBACK_TYPE) -> None:
		
		"""按事件类型注册回调（同类型可注册多个，按注册顺序依次调用）"""
		
		self.event_handlers[event_type].append(handler)
	
	async def _dispatch_event(self, event: BaseEvent) -> None:
		
		event_t		= type(event)
		handlers	= self.event_handlers.get(event_t, [])
		
		for handler in handlers:
			
			try:
				
				await handler(event)
			
			except Exception as e:
				
				DISPATCH_LOGGER.exception(
					f"分发 {event_t.__name__} 给 {_handler_name(handler)} 时"
					f"出现错误: {e}"
				)
		
		return
	
	def __aiter__(self) -> Self:
		return self
	
	async def __anext__(self) -> BaseEvent:
		
		event = await self._agen.__anext__()
		
		await self._dispatch_event(event)
		
		return event
	
	async def aclose(self) -> None:
		
		"""收尾底层流（提前 break 出遍历时调用；未启动 / 重复调用都安全）"""
		
		aclose = getattr(self._agen, "aclose", None)
		
		if aclose is not None:
			await aclose()
		
		return
	
	async def __aenter__(self) -> Self:
		return self
	
	async def __aexit__(self, *exc_info) -> None:
		await self.aclose()
