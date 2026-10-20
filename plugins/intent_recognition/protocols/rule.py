from abc		import ABC, abstractmethod
from typing		import Any
from pydantic	import ConfigDict


class BaseRule(ABC):
	
	model_config = ConfigDict(extra="forbid")
	
	@abstractmethod
	def is_hit(self, data: Any) -> bool: ...
