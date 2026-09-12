from pi_bridge	import PIToolBackend as _PIToolBackend
from typing		import Any, Dict, AsyncIterable

from ncatbot.utils	import get_log


TOOL_BACKEND_LOGGER = get_log("PIToolBackend")


class PIToolBackend(_PIToolBackend):
	
	"""重新封装初始化逻辑使其支持配置文件与ncatbot日志"""
	
	def __init__(self, config: Dict[str, Any], *args, **kwargs) -> None:
		
		cg_host	= config.get("tool_backend_host")
		cg_port	= config.get("tool_backend_port")
		
		super().__init__(host=cg_host, port=cg_port)
	
	async def _execute_tool(self, tool_name: str, tool_params: Dict[str, Any]) -> AsyncIterable[Any]:
		
		TOOL_BACKEND_LOGGER.info(f"tool {tool_name} was called with params {tool_params}")
		
		generation = super()._execute_tool(tool_name=tool_name, tool_params=tool_params)
		async for result in generation:
			yield result
		
		return