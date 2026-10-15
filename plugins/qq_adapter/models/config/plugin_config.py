from pydantic	import BaseModel, Field

from .split	import SplitConfig


class PluginConfig(BaseModel):
	
	"""qq 平台适配插件配置"""

	enable: bool = Field(default=True, description="是否启用插件")
	
	split: SplitConfig	= Field(default_factory=SplitConfig, description="输出配置")