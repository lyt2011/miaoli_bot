from pydantic	import BaseModel, Field, ConfigDict, model_validator, PrivateAttr
from typing		import Optional, Self, Dict, List
from pathlib	import Path

from .provider		import Provider, LLM
from .account		import Account
from .sub_plugin	import SubPluginConfig
from .check_pointer	import CheckPointerConfig
from .split			import SplitConfig
from .typing		import TypingConfig


class PluginConfig(BaseModel):
	
	model_config = ConfigDict(extra="allow")

	prompt_file: Optional[str]	= Field(default=None, description="系统提示词文件")
	
	provider	: str				= Field(..., description="将要使用的供应商")
	model		: str				= Field(..., description="将要使用的模型")
	providers	: List[Provider]	= Field(default_factory=list, description="供应商", min_length=1)
	
	account		: Account				= Field(..., description="账号信息配置")
	checkpointer: CheckPointerConfig	= Field(default_factory=CheckPointerConfig, description="check_pointer 数据库配置")
	sub_plugin	: SubPluginConfig		= Field(default_factory=SubPluginConfig, description="插件配置")
	split		: SplitConfig			= Field(default_factory=SplitConfig, description="分割配置")
	typing		: TypingConfig			= Field(default_factory=TypingConfig, description="打字速度配置")
	
	_prompt: str = PrivateAttr(default="")
	
	
	@property
	def prompt(self) -> str:
		
		"""
		懒加载提示词
		空文件会导致每次调用都加载，这是故意的
		"""
		
		if self.prompt_file and not self._prompt:
			self._prompt = Path(self.prompt_file).read_text(encoding="utf-8")
		
		return self._prompt
	
	@model_validator(mode="after")
	def ensure_pm_exist(self) -> Self:
		
		"""确保供应商 (provider) 与 模型 (model) 是已配置的"""
		
		providers: Dict[str, Provider] = {p.name: p for p in self.providers}
		if self.provider not in providers:
			raise ValueError(f"供应商 '{self.provider}' 未配置")
		
		models: Dict[str, LLM]	= {model.name: model for model in providers[self.provider].models}
		if self.model not in models:
			ValueError(f"供应商 '{self.provider}' 未配置 '{self.model}' 模型")
		
		return self