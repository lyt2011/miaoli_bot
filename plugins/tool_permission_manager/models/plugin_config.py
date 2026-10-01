from pydantic	import BaseModel, Field
from typing		import List

from .permission	import Permission


class PluginConfig(BaseModel):
	enable		: bool				= Field(default=False, description="设置插件启用状态")
	permissions	: List[Permission]	= Field(default_factory=list, description="权限控制表")