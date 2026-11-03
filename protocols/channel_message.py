from abc	import ABC, abstractmethod


class ChannelMessage(ABC):
	
	@abstractmethod
	def to_text(self) -> str: ...