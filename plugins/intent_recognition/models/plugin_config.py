from pydantic	import BaseModel, ConfigDict, Field
from typing		import List

from .match_	import Match


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="forbid")
	
	enable: bool = Field(default=False, description="是否启用该插件")
	
	with_path	: bool			= Field(default=True, description="注入的提示词是否携带 (from <file>) 后缀")
	matchers	: List[Match]	= Field(default_factory=list, description="匹配器")
	
