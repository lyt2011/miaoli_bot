from ncatbot.event.qq				import MessageEvent
from ncatbot						import api as nc_api
from ncatbot.types.napcat.message	import SendMessageResult
from ncatbot.types					import MessageArray

from typing	import Union, Optional, Any, Self

from .base_adapter	import BaseAdapter
from ..utils		import easier_send


# 哨兵值 用于区分None与找不到
_NULL = object()


class EventAdapter(BaseAdapter):
	
	"""为ncatbot的事件对象做鸭子类型适配"""
	
	def __init__(self, event: MessageEvent) -> None:
		self._event = event
	
	
	@classmethod
	def build(cls, event: MessageEvent) -> Self:
		return cls(event)
	
	
	@property
	def chat_id(self) -> Optional[Any]:
		return self.group_id or self.user_id
	
	@property
	def user_id(self) -> Optional[Any]:
		
		"""
		通过鸭子类型匹配
		获取 event.sender.user_id
		"""
		
		sender	= getattr(self._event, "sender", None)
		user_id	= getattr(sender, "user_id", None)
		
		return user_id
	
	@property
	def group_id(self) -> Optional[Any]:
		
		"""
		通过鸭子类型匹配
		获取 event.group_id
		"""
		
		return getattr(self._event, "group_id", None)
	
	@property
	def is_group(self) -> Optional[bool]:
		
		"""
		通过鸭子类型获取 is_group_msg 方法
		并返回其返回值
		不存在该方法或该字段为属性时则返回None
		"""
		
		is_group_msg = getattr(self._event, "is_group_msg", None)
		
		if is_group_msg and callable(is_group_msg):
			return bool(is_group_msg())
		
		return None
	
	
	async def send(
		self,
		api		: nc_api,
		message	: Union[str, MessageArray],
	) -> SendMessageResult:
		
		"""
		便捷的 send 方法
		通过调用 utils.easier_send 方法发送
		
		函数内部会自动获取 chat_id 与 is_group
		chat_id 或 is_group 不存在时会抛出 RuntimeError
		"""
		
		if self.chat_id is None or self.is_group is None:
			raise RuntimeError(f"{type(self._event).__name__} 不支持 send 方法")
	
		send_coro = easier_send(ncatbot_api=api, chat_id=self.chat_id, message=message, to_group=self.is_group)
		
		return await send_coro
	
	
	def __getattr__(self, name: str) -> Any:
		
		"""未定义的方法代理到 self._event"""
		
		value = getattr(self._event, name, _NULL)
		if value is not _NULL:
			return value
		
		raise AttributeError("适配器无该属性 事件也无该属性")