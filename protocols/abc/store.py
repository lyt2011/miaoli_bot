from abc	import ABC, abstractmethod
from typing	import Any


class StoreProtocol(ABC):
	
	@abstractmethod
	def set(self, key: str, value: Any) -> None: ...
	
	@abstractmethod
	def drop(self, key: str) -> None: ...
	
	@abstractmethod
	def clear(self) -> None: ...
	
	@abstractmethod
	def recall(self, key: str, default: Any) -> Any: ...
	
	@abstractmethod
	def contains(self, key: str) -> bool: ...
	
	@abstractmethod
	def is_empty(self) -> bool: ...