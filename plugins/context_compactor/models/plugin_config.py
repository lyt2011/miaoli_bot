from pydantic	import BaseModel, Field

from .calculate_config	import CalculateConfig
from .compact_config	import CompactConfig

class PluginConfig(BaseModel):
	
	enable: bool = Field(default=False, description="是否启用该插件")
	
	calculate	: CalculateConfig	= Field(default_factory=CalculateConfig, description="token计算配置")
	compact		: CompactConfig		= Field(default_factory=CompactConfig, description="压缩行为配置")
