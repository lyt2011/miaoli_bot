from dataclasses	import dataclass

from ...protocols	import ToolObtainanle


@dataclass
class MCPClient:
	
	reusable: bool
	client	: ToolObtainanle
