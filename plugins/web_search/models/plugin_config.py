from pydantic	import BaseModel, Field, PrivateAttr, model_validator
from typing		import Self, Literal

import os


Provider = Literal["langsearch"]


class PluginConfig(BaseModel):
	
	enable: bool	= Field(default=True, description="设置插件启用状态")
	
	provider: Provider	= Field(..., description="供应商")
	base_url: str		= Field(..., description="联网搜索用的 url")
	env_key	: str		= Field(default="SEARCH_API_KEY", description="通过该键从虚拟环境获取key")
	
	_api_key: str = PrivateAttr(default="")
	
	
	@property
	def api_key(self) -> str:
		return self._api_key
	
	@model_validator(mode="after")
	def get_key_from_env(self) -> Self:
		
		if self.env_key not in os.environ:
			return self
		
		self._api_key = os.environ[self.env_key]
		
		return self