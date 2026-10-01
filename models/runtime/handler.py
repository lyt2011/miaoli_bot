from dataclasses	import dataclass
from typing			import Callable


@dataclass
class Handler:
	priority: int
	function: Callable[..., ...]