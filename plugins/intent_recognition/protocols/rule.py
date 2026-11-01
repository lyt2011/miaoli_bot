from pydantic	import ConfigDict

from typing	import Any
from abc	import ABC, abstractmethod


class BaseRule(ABC):
	
	model_config = ConfigDict(extra="forbid")
	
	@abstractmethod
	def is_hit(self, data: Any) -> bool: ...
