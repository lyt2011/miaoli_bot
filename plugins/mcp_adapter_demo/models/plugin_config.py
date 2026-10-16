from pydantic	import BaseModel, Field, model_validator
from typing		import List, Self

from .mcp_server	import MCPServer


class PluginConfig(BaseModel):
	
	enable		: bool				= Field(default=True, description="插件开关")
	tool_prefix	: bool				= Field(default=True, description="是否启用工具前缀")
	mcps		: List[MCPServer]	= Field(default_factory=list, description="mcp 服务器配置")
	
	
	@model_validator(mode="after")
	def server_dedup(self) -> Self:
		
		"""对重复的服务器名字抛出错误"""
		
		raw_names	= [mcp.name for mcp in self.mcps]
		duplicates	= {name for name in raw_names if raw_names.count(name) > 1}
		
		if duplicates:
			raise ValueError(f"有以下服务器名重复了: {duplicates}")
		
		return self
