from pydantic	import BaseModel, Field

from .workflows	import Workflow

from typing		import List


class PluginConfig(BaseModel):
	
	enable		: bool				= Field(default=False, description="是否启用该插件")
	workflows	: List[Workflow]	= Field(default_factory=list, description="工作流")
