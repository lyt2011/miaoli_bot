from ...protocols	import ToolObtainanle

from dataclasses	import dataclass


@dataclass
class MCPClient:
	
	reusable: bool
	client	: ToolObtainanle
