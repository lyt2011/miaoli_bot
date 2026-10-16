from pydantic	import BaseModel, Field
from typing		import List

from .permission	import Permission


class PluginConfig(BaseModel):
	
	enable	: bool	= Field(default=True, description="设置插件启用状态 (默认开启 未配置时也不会放过任何工具)")
	debug	: bool	= Field(default=True, description="对于未配置的工具打警告日志 (仅影响日志输出 不影响权限判定)")
	
	permissions: List[Permission]	= Field(default_factory=list, description="权限控制表")