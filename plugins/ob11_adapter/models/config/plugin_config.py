from pydantic	import BaseModel, Field


class PluginConfig(BaseModel):
	
	"""ncatbot OB11 事件适配插件配置"""
	
	enable: bool = Field(default=True, description="是否启用插件")
