from typing			import Any
from dataclasses	import dataclass


@dataclass(slots=True, frozen=True)
class DispatchResult:
	
	is_handled	: bool	= True
	result		: Any	= None
