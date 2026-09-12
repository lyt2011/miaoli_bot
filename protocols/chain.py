from abc	import ABC, abstractmethod
from typing	import Any

from .handler	import Handler
from ..models	import DispatchResult


class ChainProtocol(ABC):
	
	@abstractmethod
	def register_handler(self, handler: Handler) -> None: ...
	
	@abstractmethod
	async def dispatch(self, data: Any) -> DispatchResult: ...
