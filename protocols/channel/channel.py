from .message	import ChannelMessage

from abc	import ABC, abstractmethod


class BaseChannel(ABC):
	
	@property
	@abstractmethod
	def name(self) -> str: ...
	
	@abstractmethod
	async def drain(self) -> ChannelMessage:
		"""取走通道里未读消息"""
