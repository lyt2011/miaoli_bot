from pydantic	import BaseModel, Field, ConfigDict, model_validator

from .buffer_config			import BufferConfig
from .account_config		import AccountConfig
from .provider_config		import Provider, LLM
from .sub_plugin_config		import SubPluginConfig
from .reply_split_config	import ReplySplitConfig
from .typing_speed_config	import TypingSpeedConfig
from .checkpointer_config	import CheckpointerConfig

from typing	import Self, Dict, List


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="allow")
	
	provider	: str				= Field(..., description="将要使用的供应商")
	model		: str				= Field(..., description="将要使用的模型")
	providers	: List[Provider]	= Field(default_factory=list, description="供应商", min_length=1)
	
	account		: AccountConfig				= Field(..., description="账号信息配置")
	buffer		: BufferConfig				= Field(default_factory=BufferConfig, description="事件缓冲区配置")
	checkpointer: CheckpointerConfig	= Field(default_factory=CheckpointerConfig, description="check_pointer 数据库配置")
	sub_plugin	: SubPluginConfig		= Field(default_factory=SubPluginConfig, description="插件配置")
	split		: ReplySplitConfig			= Field(default_factory=ReplySplitConfig, description="分割配置")
	typing		: TypingSpeedConfig			= Field(default_factory=TypingSpeedConfig, description="打字速度配置")
	
	@model_validator(mode="after")
	def ensure_pm_exist(self) -> Self:
		
		"""确保供应商 (provider) 与 模型 (model) 是已配置的"""
		
		providers: Dict[str, Provider] = {p.name: p for p in self.providers}
		if self.provider not in providers:
			raise ValueError(f"供应商 '{self.provider}' 未配置")
		
		models: Dict[str, LLM]	= {model.name: model for model in providers[self.provider].models}
		if self.model not in models:
			raise ValueError(f"供应商 '{self.provider}' 未配置 '{self.model}' 模型")
		
		return self
