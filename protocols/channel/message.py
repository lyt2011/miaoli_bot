from abc	import ABC, abstractmethod


class BaseChannelMessage(ABC):
	
	@property
	@abstractmethod
	def thread_id(self) -> str: ...
	
	@property
	@abstractmethod
	def platform(self) -> str: ...
	
	@abstractmethod
	def to_text(self) -> str: ...
