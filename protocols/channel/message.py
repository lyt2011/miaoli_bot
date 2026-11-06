from abc	import ABC, abstractmethod

from typing	import Any, Union


class ChannelMessage(ABC):
	
	@property
	@abstractmethod
	def raw(self) -> Any: ...
	
	@abstractmethod
	def to_structured(self) -> Union[dict, list, str]: ...
