from .message	import BaseChannelMessage

from abc	import ABC, abstractmethod
from typing	import List


class BaseChannel(ABC):
	
	@property
	@abstractmethod
	def name(self) -> str: ...
	
	@abstractmethod
	async def drain(self) -> List[BaseChannelMessage]: ... # 自己处理去重 框架只负责拿
	
	@abstractmethod
	async def reply(self, thread_id: str, text: str) -> None: ...