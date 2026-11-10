from .message	import BaseChannelMessage, Content

from abc	import ABC, abstractmethod
from typing	import FrozenSet, List


class BaseChannel(ABC):
	
	@property
	@abstractmethod
	def platforms(self) -> FrozenSet[str]: ...
	
	@property
	@abstractmethod
	def name(self) -> str: ...
	
	@abstractmethod
	async def drain(self) -> List[BaseChannelMessage]: ... # 自己处理去重 框架只负责拿
	
	@abstractmethod
	async def reply(self, platform: str, thread_id: str, content: Content) -> None: ...