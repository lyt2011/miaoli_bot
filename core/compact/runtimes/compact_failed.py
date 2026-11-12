from typing			import Optional
from dataclasses	import dataclass, field


@dataclass(frozen=True)
class CompactFailed:
	
	reason		: str
	exception	: Optional[Exception]	= field(default=None)