from dataclasses	import dataclass
from typing			import Any, Awaitable, Callable


@dataclass
class Handler:
	priority: int
	function: Callable[..., Awaitable[Any]]