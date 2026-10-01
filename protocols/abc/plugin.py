from __future__	import annotations

from abc	import ABC, abstractmethod
from typing	import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
	from ...core	import Registry


class PluginProtocol(ABC):
	
	def __init__(self, config: Dict[str, Any], registry: Registry) -> None:
		self.config		= config
		self.registry	= registry
	
	@abstractmethod
	async def on_load(self) -> None: ...
	
	@abstractmethod
	async def on_close(self) -> None: ...
