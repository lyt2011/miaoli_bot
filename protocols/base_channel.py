from .channel_message	import ChannelMessage

from typing	import List
from abc	import ABC, abstractmethod


class BaseChannel(ABC):
	
	@property
	@abstractmethod
	def name(self) -> str: ...
	
	@abstractmethod
	async def drain(self) -> List[ChannelMessage]:
		"""取走通道里全部未读消息 按「旧 → 新」返回"""
