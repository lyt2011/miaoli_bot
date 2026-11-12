from ...protocols	import ToolObtainable

from dataclasses	import dataclass


@dataclass
class MCPClient:
	
	reusable: bool
	client	: ToolObtainable
