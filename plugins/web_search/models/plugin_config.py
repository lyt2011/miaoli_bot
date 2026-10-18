from pydantic	import BaseModel, Field
from typing		import Literal


Adapter = Literal["langsearch", "deepseek"]


class PluginConfig(BaseModel):
	
	enable: bool	= Field(default=True, description="设置插件启用状态")
	
	adapter	: Adapter	= Field(..., description="供应商")
	api_url	: str		= Field(..., description="联网搜索用的 url")
	api_key	: str		= Field(..., description="搜索api key")
