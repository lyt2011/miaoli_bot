from dataclasses	import dataclass
from typing			import Any


@dataclass(slots=True, frozen=True)
class DispatchResult:
	
	is_handled	: bool	= True
	result		: Any	= None