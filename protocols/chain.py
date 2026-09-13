from abc	import ABC, abstractmethod
from typing	import Any

from .parser	import Parser
from ..models	import DispatchResult


class ChainProtocol(ABC):
	
	@abstractmethod
	def register_parser(self, parser: Parser) -> None: ...
	
	@abstractmethod
	async def dispatch(self, data: Any) -> DispatchResult: ...
