from __future__	import annotations

from dataclasses	import dataclass, field
from enum			import Enum, auto
from typing			import TYPE_CHECKING, Optional

if TYPE_CHECKING:
	from .plugin	import Plugin


class Status(Enum):
	
	PREPARED	= auto()
	LOADED		= auto()
	UNLOADED	= auto()
	ERRED		= auto()


@dataclass
class PluginEntity:
	
	"""插件登记表的一行 持有插件本身与它的当前状态"""
	
	plugin		: Plugin
	status		: Status					= field(default=Status.PREPARED)
	exception	: Optional[Exception]		= field(default=None)
	
	def is_prepared(self) -> bool:
		return self.status is Status.PREPARED
	
	def is_loaded(self) -> bool:
		return self.status is Status.LOADED
	
	def is_unloaded(self) -> bool:
		return self.status is Status.UNLOADED
	
	def is_erred(self) -> bool:
		return self.status is Status.ERRED
	
	def mark_prepared(self) -> None:
		self.status = Status.PREPARED
	
	def mark_loaded(self) -> None:
		self.status = Status.LOADED
	
	def mark_unloaded(self) -> None:
		self.status = Status.UNLOADED
	
	def mark_erred(self, exception: Exception) -> None:
		self.status, self.exception = Status.ERRED, exception
