from typing	import Any, List

from ..models.runtimes	import MCPClient
from ..protocols		import ToolObtainanle


class MCPClientRegistry:
	
	def __init__(self) -> None:
		
		self.clients		: List[MCPClient]	= []
		self._cached_tools	: List[Any]			= []
	
	def register_client(self, client: ToolObtainanle, reusable: bool) -> None:
		
		"""注册客户端 自动去重(实例级)"""
		
		# 过滤掉重复的客户端
		if client in [client_.client for client_ in self.clients]:
			return None
		
		self.clients.append(MCPClient(client=client, reusable=reusable))
		
	async def get_tools(self) -> List[Any]:
		
		"""
		统一的工具获取
		注意 由于假设了工具的类型是 Any，导致本方法没有去重功能，调用点需要手动去重
		"""
		
		# 创建工具列表并原地扩展已缓存的工具
		tool_list = []
		tool_list.extend(self._cached_tools)
		
		for mcp_client in list(self.clients):
			
			tools = await mcp_client.client.get_tools()
			tool_list.extend(tools)
			
			# 可复用则直接删掉该客户端并缓存工具
			if mcp_client.reusable:
				self.clients.remove(mcp_client)
				self._cached_tools.extend(tools)
				
		return tool_list
