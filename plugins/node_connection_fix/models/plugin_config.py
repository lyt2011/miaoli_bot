from pydantic	import BaseModel, Field

class PluginConfig(BaseModel):
	
	enable: bool	= Field(default=True, description="设置插件启用状态")
