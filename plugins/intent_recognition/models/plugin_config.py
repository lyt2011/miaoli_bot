from pydantic	import BaseModel, ConfigDict, Field
from typing		import List

from .match_	import Match


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="forbid")
	
	enable: bool = Field(default=False, description="是否启用该插件")
	
	matchers: List[Match]	= Field(default_factory=list, description="匹配器")
	
