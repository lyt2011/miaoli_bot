from dataclasses	import dataclass, field
from typing			import Any, List


@dataclass(slots=True, frozen=True)
class ParseResult:
	
	event	: Any		= None
	segments: List[Any] = field(default_factory=list)