from abc	import ABC, abstractmethod
from typing	import Any, Dict, List, Union


Content = Union[str, List[Dict[str, Any]]]


class BaseChannelMessage(ABC):
	
	@property
	@abstractmethod
	def thread_id(self) -> str: ...
	
	@property
	@abstractmethod
	def platform(self) -> str: ...
	
	def __str__(self) -> str:
		return (f"<{type(self).__name__} "
			f"{self.platform}:{self.thread_id}>")
	
	@abstractmethod
	def to_content(self) -> Content: ...
